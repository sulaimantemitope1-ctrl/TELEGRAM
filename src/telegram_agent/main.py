"""Application entrypoint for the Telegram AI Agent."""

from __future__ import annotations

import logging
import sys

from telegram_agent.agents.computer_action import ComputerActionAgent
from telegram_agent.agents.coordinator import CoordinatorAgent
from telegram_agent.agents.response import ResponseAgent
from telegram_agent.agents.verification import VerificationAgent
from telegram_agent.bot.telegram_bot import build_telegram_application
from telegram_agent.config import Settings
from telegram_agent.llm.claude_client import ClaudeReasoningClient
from telegram_agent.safety.approval import PendingApprovalManager
from telegram_agent.tools.mac_tools import MacTools


def configure_logging() -> None:
    """Configure application logging while suppressing HTTP client URL token logs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Prevent httpx/httpcore from logging Telegram bot token in request URLs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    settings = Settings.from_env()
    try:
        settings.validate_for_runtime()
    except ValueError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    if not settings.allowed_telegram_user_ids:
        logger.warning(
            "ALLOWED_TELEGRAM_USER_IDS is empty. Use /myid in Telegram to find your ID and add it to .env."
        )

    mac_tools = MacTools(screenshots_dir=settings.screenshots_dir)
    reasoning_client = ClaudeReasoningClient(
        api_key=settings.anthropic_api_key,
        model=settings.claude_model,
        approved_apps=settings.approved_apps,
    )
    action_agent = ComputerActionAgent(mac_tools=mac_tools, settings=settings)
    verification_agent = VerificationAgent(mac_tools=mac_tools)
    response_agent = ResponseAgent()
    approval_manager = PendingApprovalManager(
        ttl_seconds=settings.approval_timeout_seconds
    )

    coordinator = CoordinatorAgent(
        settings=settings,
        reasoning_client=reasoning_client,
        action_agent=action_agent,
        verification_agent=verification_agent,
        response_agent=response_agent,
        approval_manager=approval_manager,
    )

    app = build_telegram_application(
        settings=settings,
        coordinator=coordinator,
        approval_manager=approval_manager,
    )
    logger.info("Starting Telegram AI Agent polling (model=%s)...", settings.claude_model)
    app.run_polling()


if __name__ == "__main__":
    main()
