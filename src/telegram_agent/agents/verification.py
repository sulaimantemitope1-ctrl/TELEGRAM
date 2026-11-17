"""Verification Agent: confirms that requested computer actions actually occurred."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List

from telegram_agent.models import (
    ActionType,
    ExecutionResult,
    ProposedAction,
    VerificationResult,
)
from telegram_agent.tools.mac_tools import MacTools


class VerificationAgent:
    """Checks evidence that an executed action succeeded."""

    def __init__(self, mac_tools: MacTools) -> None:
        self._tools = mac_tools

    async def verify(
        self,
        action: ProposedAction,
        execution: ExecutionResult,
        retry_delay_seconds: float = 0.5,
    ) -> VerificationResult:
        """Verify the outcome of an ExecutionResult. Never claims success without evidence."""
        if not execution.success:
            return VerificationResult(
                verified=False,
                failure_reason=execution.error or execution.summary,
            )

        checks: List[str] = []

        if action.action in {ActionType.OPEN_APP, ActionType.OPEN_URL}:
            app_name = str(execution.details.get("application") or action.application or "Google Chrome")
            running = await self._tools.is_app_running(app_name)
            if not running:
                await asyncio.sleep(retry_delay_seconds)
                running = await self._tools.is_app_running(app_name)

            if not running:
                return VerificationResult(
                    verified=False,
                    checks=checks,
                    failure_reason=f"Could not verify that '{app_name}' is running.",
                )
            checks.append(f"Confirmed '{app_name}' process is running.")

            if action.take_screenshot_after:
                shot_ok, shot_reason = self._verify_screenshot_file(execution.screenshot_path)
                if not shot_ok:
                    return VerificationResult(
                        verified=False,
                        checks=checks,
                        failure_reason=shot_reason,
                    )
                checks.append("Confirmed follow-up screenshot was captured.")

            return VerificationResult(
                verified=True,
                checks=checks,
                evidence_screenshot_path=execution.screenshot_path,
            )

        if action.action == ActionType.TAKE_SCREENSHOT:
            shot_ok, shot_reason = self._verify_screenshot_file(execution.screenshot_path)
            if not shot_ok:
                return VerificationResult(
                    verified=False,
                    failure_reason=shot_reason,
                )
            checks.append("Confirmed screenshot file exists and is non-empty.")
            return VerificationResult(
                verified=True,
                checks=checks,
                evidence_screenshot_path=execution.screenshot_path,
            )

        if action.action == ActionType.OPEN_FILE:
            file_path = execution.details.get("file_path") or action.file_path or ""
            resolved = Path(file_path).expanduser().resolve()
            if not resolved.exists():
                return VerificationResult(
                    verified=False,
                    failure_reason=f"File does not exist: {resolved}",
                )
            checks.append(f"Confirmed target file exists: {resolved.name}")
            return VerificationResult(verified=True, checks=checks)

        if action.action == ActionType.SYSTEM_INFO:
            if not execution.details:
                return VerificationResult(
                    verified=False,
                    failure_reason="System info returned empty details.",
                )
            checks.append("Confirmed system information fields were collected.")
            return VerificationResult(verified=True, checks=checks)

        return VerificationResult(
            verified=False,
            failure_reason=f"No verification strategy for action '{action.action.value}'.",
        )

    @staticmethod
    def _verify_screenshot_file(path: str | None) -> tuple[bool, str]:
        if not path:
            return False, "No screenshot path was produced."
        file_path = Path(path)
        if not file_path.exists():
            return False, f"Screenshot file missing at {file_path}."
        if file_path.stat().st_size == 0:
            return False, f"Screenshot file is empty at {file_path}."
        return True, "OK"
