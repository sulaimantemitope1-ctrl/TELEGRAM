"""Tests for Telegram user authorization and bot command access."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram_agent.bot.telegram_bot import TelegramBotController
from telegram_agent.config import Settings
from telegram_agent.safety.approval import PendingApprovalManager
from telegram_agent.safety.auth import is_user_authorized


def test_is_user_authorized():
    allowed = frozenset({111, 222})
    assert is_user_authorized(111, allowed) is True
    assert is_user_authorized(222, allowed) is True
    assert is_user_authorized(999, allowed) is False
    assert is_user_authorized(None, allowed) is False
    assert is_user_authorized(111, frozenset()) is False


@pytest.mark.asyncio
async def test_myid_works_for_any_user():
    settings = Settings(
        telegram_bot_token="token",
        anthropic_api_key="key",
        allowed_telegram_user_ids=frozenset({111}),
    )
    controller = TelegramBotController(
        settings=settings,
        coordinator=MagicMock(),
        approval_manager=PendingApprovalManager(),
    )

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=55555),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    await controller.cmd_myid(update, context=None)
    update.message.reply_text.assert_awaited_once_with("Your Telegram user ID is: 55555")


@pytest.mark.asyncio
async def test_unauthorized_user_rejected_on_text_message():
    settings = Settings(
        telegram_bot_token="token",
        anthropic_api_key="key",
        allowed_telegram_user_ids=frozenset({111}),
    )
    coordinator = MagicMock()
    coordinator.handle_message = AsyncMock()
    controller = TelegramBotController(
        settings=settings,
        coordinator=coordinator,
        approval_manager=PendingApprovalManager(),
    )

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=999),
        effective_chat=SimpleNamespace(id=999),
        message=SimpleNamespace(text="Open Chrome", reply_text=AsyncMock()),
    )
    await controller.handle_text(update, context=None)

    coordinator.handle_message.assert_not_awaited()
    reply = update.message.reply_text.call_args[0][0]
    assert "Unauthorized" in reply
