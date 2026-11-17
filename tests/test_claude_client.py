"""Tests for ClaudeReasoningClient using a mocked Anthropic client."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from telegram_agent.config import DEFAULT_APPROVED_APPS
from telegram_agent.llm.claude_client import ClaudeReasoningClient
from telegram_agent.models import ActionType


@pytest.mark.asyncio
async def test_claude_interprets_open_google_in_chrome():
    mock_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            type="tool_use",
                            name="propose_action",
                            input={
                                "action": "open_url",
                                "application": "Google Chrome",
                                "url": "https://www.google.com",
                                "target": "Google",
                                "take_screenshot_after": False,
                                "reason": "User asked to open Google in Chrome.",
                                "confidence": 0.98,
                            },
                        )
                    ]
                )
            )
        )
    )

    reasoning = ClaudeReasoningClient(
        api_key="test-key",
        model="claude-sonnet-4-20250514",
        approved_apps=DEFAULT_APPROVED_APPS,
        client=mock_client,
    )

    result = await reasoning.interpret("Open Google in Chrome.")
    assert result.action == ActionType.OPEN_URL
    assert result.application == "Google Chrome"
    assert result.url == "https://www.google.com"
    assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_claude_fallback_to_clarify_on_unparseable_response():
    mock_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    content=[SimpleNamespace(type="text", text="Not valid JSON")]
                )
            )
        )
    )

    reasoning = ClaudeReasoningClient(
        api_key="test-key",
        model="claude-sonnet-4-20250514",
        approved_apps=DEFAULT_APPROVED_APPS,
        client=mock_client,
    )

    result = await reasoning.interpret("Do something")
    assert result.action == ActionType.CLARIFY
    assert result.clarification_question is not None
