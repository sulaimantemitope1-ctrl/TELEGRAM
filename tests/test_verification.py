"""Tests for VerificationAgent."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram_agent.agents.verification import VerificationAgent
from telegram_agent.models import ActionType, ExecutionResult, ProposedAction


@pytest.mark.asyncio
async def test_verify_open_url_fails_when_app_not_running(tmp_path: Path):
    tools = MagicMock()
    tools.is_app_running = AsyncMock(return_value=False)
    verifier = VerificationAgent(mac_tools=tools)

    action = ProposedAction(
        action=ActionType.OPEN_URL,
        application="Google Chrome",
        url="https://www.google.com",
    )
    execution = ExecutionResult(
        success=True,
        action=ActionType.OPEN_URL,
        summary="Opened Google",
        details={"application": "Google Chrome"},
    )

    result = await verifier.verify(action, execution, retry_delay_seconds=0.0)
    assert result.verified is False
    assert "not verify" in (result.failure_reason or "").lower()


@pytest.mark.asyncio
async def test_verify_screenshot_succeeds_when_file_exists(tmp_path: Path):
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"png-bytes")

    verifier = VerificationAgent(mac_tools=MagicMock())
    action = ProposedAction(action=ActionType.TAKE_SCREENSHOT)
    execution = ExecutionResult(
        success=True,
        action=ActionType.TAKE_SCREENSHOT,
        summary="Captured screenshot",
        screenshot_path=str(shot),
    )

    result = await verifier.verify(action, execution)
    assert result.verified is True
    assert result.evidence_screenshot_path == str(shot)


@pytest.mark.asyncio
async def test_verify_screenshot_fails_when_file_missing(tmp_path: Path):
    verifier = VerificationAgent(mac_tools=MagicMock())
    action = ProposedAction(action=ActionType.TAKE_SCREENSHOT)
    execution = ExecutionResult(
        success=True,
        action=ActionType.TAKE_SCREENSHOT,
        summary="Captured screenshot",
        screenshot_path=str(tmp_path / "missing.png"),
    )

    result = await verifier.verify(action, execution)
    assert result.verified is False
    assert "missing" in (result.failure_reason or "").lower()
