"""Telegram bot handlers connecting Telegram updates to CoordinatorAgent."""

from __future__ import annotations

import logging
from pathlib import Path

import anthropic
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from telegram_agent.agents.coordinator import CoordinatorAgent
from telegram_agent.config import Settings
from telegram_agent.models import AgentResponse
from telegram_agent.safety.approval import PendingApprovalManager
from telegram_agent.safety.auth import is_user_authorized

logger = logging.getLogger(__name__)


class TelegramBotController:
    """Handles Telegram commands, messages, and human-approval callbacks."""

    def __init__(
        self,
        settings: Settings,
        coordinator: CoordinatorAgent,
        approval_manager: PendingApprovalManager,
    ) -> None:
        self._settings = settings
        self._coordinator = coordinator
        self._approvals = approval_manager

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        user_id = update.effective_user.id
        authorized = is_user_authorized(user_id, self._settings.allowed_telegram_user_ids)
        status_note = (
            "You are authorized to send instructions."
            if authorized
            else "You are not yet authorized. Use /myid to get your numeric ID and add it to ALLOWED_TELEGRAM_USER_IDS."
        )
        await update.message.reply_text(
            "Telegram AI Agent is online.\n\n"
            f"{status_note}\n\n"
            "Commands:\n"
            "/myid - Show your numeric Telegram user ID\n"
            "/help - Show supported actions and examples\n"
            "/status - Show agent configuration"
        )

    async def cmd_myid(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        user_id = update.effective_user.id
        await update.message.reply_text(f"Your Telegram user ID is: {user_id}")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        await update.message.reply_text(
            "You can send natural-language instructions, such as:\n"
            "- \"Open Google in Chrome.\"\n"
            "- \"Open Google in Chrome and take a screenshot.\"\n"
            "- \"Take a screenshot and send it to me.\"\n"
            "- \"Open Notes.\"\n"
            "- \"Show me basic Mac system info.\"\n\n"
            "Commands:\n"
            "/start - Check bot connection\n"
            "/myid - Get your numeric Telegram ID\n"
            "/status - View current agent settings (authorized users only)"
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        user_id = update.effective_user.id
        if not is_user_authorized(user_id, self._settings.allowed_telegram_user_ids):
            await update.message.reply_text(
                "Unauthorized: your Telegram user ID is not permitted to view status."
            )
            return

        apps = ", ".join(sorted(self._settings.approved_apps))
        await update.message.reply_text(
            "Agent Status:\n"
            f"- Claude Model: {self._settings.claude_model}\n"
            f"- Require Approval (Dangerous): {self._settings.require_approval_for_dangerous}\n"
            f"- Always Require Approval: {self._settings.always_require_approval}\n"
            f"- Approved Apps: {apps}"
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user or not update.effective_chat:
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not is_user_authorized(user_id, self._settings.allowed_telegram_user_ids):
            logger.warning("Rejected unauthorized message from user_id=%s", user_id)
            await update.message.reply_text(
                "Unauthorized: your Telegram user ID is not permitted to control this Mac."
            )
            return

        text = (update.message.text or "").strip()
        if not text:
            return

        try:
            response = await self._coordinator.handle_message(
                user_id=user_id,
                chat_id=chat_id,
                message=text,
            )
        except anthropic.APIError as exc:
            logger.exception("Anthropic API error while handling Telegram message")
            await update.message.reply_text(
                f"AI service error ({type(exc).__name__}): {exc.message}"
            )
            return
        except Exception as exc:
            logger.exception("Error handling Telegram message")
            await update.message.reply_text(
                f"An unexpected error occurred ({type(exc).__name__}). Check the Terminal logs for details."
            )
            return

        await self._send_agent_response(update, response)

    async def handle_approval_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        if not query or not update.effective_user:
            return

        await query.answer()
        user_id = update.effective_user.id

        if not is_user_authorized(user_id, self._settings.allowed_telegram_user_ids):
            await query.edit_message_text(
                "Unauthorized: you are not permitted to approve or deny actions."
            )
            return

        data = query.data or ""
        if ":" not in data:
            return
        decision, approval_id = data.split(":", 1)

        pending = self._approvals.pop_for_user(approval_id, user_id)
        if pending is None:
            await query.edit_message_text(
                "This approval request has expired or is no longer valid."
            )
            return

        if decision == "deny":
            await query.edit_message_text("Action cancelled by user.")
            return

        if decision == "approve":
            await query.edit_message_text("Approved. Executing action...")
            try:
                response = await self._coordinator.execute_approved_action(pending.action)
            except Exception:
                logger.exception("Error executing approved action")
                await query.message.reply_text(
                    "An unexpected error occurred while executing the approved action."
                )
                return

            await self._send_agent_response(update, response)

    async def _send_agent_response(
        self, update: Update, response: AgentResponse
    ) -> None:
        target_message = update.effective_message
        if target_message is None:
            return

        if response.requires_approval and response.approval_id:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Approve", callback_data=f"approve:{response.approval_id}"
                        ),
                        InlineKeyboardButton(
                            "Deny", callback_data=f"deny:{response.approval_id}"
                        ),
                    ]
                ]
            )
            await target_message.reply_text(response.text, reply_markup=keyboard)
            return

        if response.screenshot_path:
            shot_file = Path(response.screenshot_path)
            if shot_file.exists():
                caption = response.text[:1024]
                with shot_file.open("rb") as photo_fh:
                    await target_message.reply_photo(photo=photo_fh, caption=caption)
                if len(response.text) > 1024:
                    await target_message.reply_text(response.text[1024:])
                return

        await target_message.reply_text(response.text)


def build_telegram_application(
    settings: Settings,
    coordinator: CoordinatorAgent,
    approval_manager: PendingApprovalManager,
) -> Application:
    """Build and configure the python-telegram-bot Application."""
    controller = TelegramBotController(
        settings=settings,
        coordinator=coordinator,
        approval_manager=approval_manager,
    )

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", controller.cmd_start))
    app.add_handler(CommandHandler("myid", controller.cmd_myid))
    app.add_handler(CommandHandler("help", controller.cmd_help))
    app.add_handler(CommandHandler("status", controller.cmd_status))
    app.add_handler(CallbackQueryHandler(controller.handle_approval_callback))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, controller.handle_text)
    )
    return app
