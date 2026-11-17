"""End-to-end tests for CoordinatorAgent workflow."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram_agent.agents.computer_action import ComputerActionAgent
from telegram_agent.agents.coordinator import CoordinatorAgent
from telegram_agent.agents.response import ResponseAgent
from telegram_agent.agents.verification import VerificationAgent
from telegram_agent.config import Settings
from telegram_agent.models import ActionType, ProposedAction
from telegram_agent.safety.approval import PendingApprovalManager


def _build_coordinator(
    tmp_path: Path,
    proposed: ProposedAction,
    always_approve: bool = False,
):
    settings = Settings(
        telegram_bot_token="token",
        anthropic_api_key="key",
        allowed_telegram_user_ids=frozenset({100}),
        always_require_approval=always_approve,
        screenshots_dir=tmp_path,
    )

    reasoning = MagicMock()
    reasoning.interpret = AsyncMock(return_value=proposed)

    shot_file = tmp_path / "evidence.png"
    shot_file.write_bytes(b"\x89PNG\r\n\x1a\nevidence")

    mac_tools = MagicMock()
    mac_tools.open_url = AsyncMock(return_value=(True, "Opened 'https://www.google.com' in 'Google Chrome'."))
    mac_tools.open_application = AsyncMock(return_value=(True, "Opened application 'Terminal'."))
    mac_tools.take_screenshot = AsyncMock(return_value=(True, str(shot_file), "Captured screenshot: evidence.png"))
    mac_tools.is_app_running = AsyncMock(return_value=True)

    action_agent = ComputerActionAgent(mac_tools=mac_tools, settings=settings)
    verification_agent = VerificationAgent(mac_tools=mac_tools)
    response_agent = ResponseAgent()
    approvals = PendingApprovalManager()

    coordinator = CoordinatorAgent(
        settings=settings,
        reasoning_client=reasoning,
        action_agent=action_agent,
        verification_agent=verification_agent,
        response_agent=response_agent,
        approval_manager=approvals,
    )
    return coordinator, mac_tools, approvals


@pytest.mark.asyncio
async def test_example_journey_open_google_and_screenshot(tmp_path: Path):
    proposed = ProposedAction(
        action=ActionType.OPEN_URL,
        application="Google Chrome",
        url="https://www.google.com",
        target="Google",
        take_screenshot_after=True,
        reason="Open Google in Chrome and take a screenshot.",
    )
    coordinator, mac_tools, _ = _build_coordinator(tmp_path, proposed)

    response = await coordinator.handle_message(
        user_id=100, chat_id=100, message="Open Google in Chrome and take a screenshot."
    )

    assert response.is_error is False
    assert response.requires_approval is False
    assert response.screenshot_path is not None
    assert "Done:" in response.text
    assert "Verification:" in response.text
    mac_tools.open_url.assert_awaited_once()
    mac_tools.take_screenshot.assert_awaited_once()


@pytest.mark.asyncio
async def test_ambiguous_request_asks_clarification(tmp_path: Path):
    proposed = ProposedAction(
        action=ActionType.CLARIFY,
        clarification_question="Which application would you like me to open?",
        reason="Ambiguous target.",
    )
    coordinator, mac_tools, _ = _build_coordinator(tmp_path, proposed)

    response = await coordinator.handle_message(
        user_id=100, chat_id=100, message="Open it"
    )

    assert "Clarification needed" in response.text
    assert "Which application" in response.text
    mac_tools.open_url.assert_not_awaited()
    mac_tools.open_application.assert_not_awaited()


@pytest.mark.asyncio
async def test_sensitive_action_pauses_for_human_approval(tmp_path: Path):
    proposed = ProposedAction(
        action=ActionType.OPEN_APP,
        application="Terminal",
        reason="User asked to open Terminal.",
    )
    coordinator, mac_tools, approvals = _build_coordinator(tmp_path, proposed)

    response = await coordinator.handle_message(
        user_id=100, chat_id=100, message="Open Terminal"
    )

    assert response.requires_approval is True
    assert response.approval_id is not None
    mac_tools.open_application.assert_not_awaited()

    pending = approvals.pop_for_user(response.approval_id, user_id=100)
    assert pending is not None
    final_response = await coordinator.execute_approved_action(pending.action)
    assert final_response.is_error is False
    assert "Done:" in final_response.text
    mac_tools.open_application.assert_awaited_once()
