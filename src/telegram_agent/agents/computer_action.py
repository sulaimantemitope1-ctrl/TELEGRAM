"""Computer Action Agent: executes approved actions on the local Mac."""

from __future__ import annotations

import asyncio
from typing import Optional

from telegram_agent.config import Settings
from telegram_agent.models import ActionType, ExecutionResult, ProposedAction
from telegram_agent.safety.policy import normalize_app_name
from telegram_agent.tools.mac_tools import MacTools


class ComputerActionAgent:
    """Executes only policy-approved actions via MacTools."""

    def __init__(self, mac_tools: MacTools, settings: Settings) -> None:
        self._tools = mac_tools
        self._settings = settings

    async def execute(
        self, action: ProposedAction, render_wait_seconds: float = 1.5
    ) -> ExecutionResult:
        """Perform the approved action and optionally capture a follow-up screenshot."""
        if action.action == ActionType.OPEN_APP:
            app_name = normalize_app_name(
                action.application or "", self._settings.approved_apps
            )
            ok, msg = await self._tools.open_application(app_name)
            screenshot_path: Optional[str] = None
            if ok and action.take_screenshot_after:
                await asyncio.sleep(render_wait_seconds)
                shot_ok, shot_path, shot_msg = await self._tools.take_screenshot()
                if shot_ok:
                    screenshot_path = shot_path
                else:
                    msg = f"{msg} (Screenshot failed: {shot_msg})"
            return ExecutionResult(
                success=ok,
                action=action.action,
                summary=msg,
                details={"application": app_name},
                screenshot_path=screenshot_path,
                error=None if ok else msg,
            )

        if action.action == ActionType.OPEN_URL:
            app_name = normalize_app_name(
                action.application or "Google Chrome", self._settings.approved_apps
            )
            url = action.url or ""
            ok, msg = await self._tools.open_url(url, app_name=app_name)
            screenshot_path = None
            if ok and action.take_screenshot_after:
                await asyncio.sleep(render_wait_seconds)
                shot_ok, shot_path, shot_msg = await self._tools.take_screenshot()
                if shot_ok:
                    screenshot_path = shot_path
                else:
                    msg = f"{msg} (Screenshot failed: {shot_msg})"
            return ExecutionResult(
                success=ok,
                action=action.action,
                summary=msg,
                details={"application": app_name, "url": url},
                screenshot_path=screenshot_path,
                error=None if ok else msg,
            )

        if action.action == ActionType.TAKE_SCREENSHOT:
            ok, shot_path, msg = await self._tools.take_screenshot()
            return ExecutionResult(
                success=ok,
                action=action.action,
                summary=msg,
                screenshot_path=shot_path,
                error=None if ok else msg,
            )

        if action.action == ActionType.OPEN_FILE:
            file_path = action.file_path or ""
            ok, msg = await self._tools.open_file(file_path)
            return ExecutionResult(
                success=ok,
                action=action.action,
                summary=msg,
                details={"file_path": file_path},
                error=None if ok else msg,
            )

        if action.action == ActionType.SYSTEM_INFO:
            info = await self._tools.get_system_info()
            return ExecutionResult(
                success=True,
                action=action.action,
                summary="Retrieved Mac system information.",
                details=info,
            )

        return ExecutionResult(
            success=False,
            action=action.action,
            summary=f"Action '{action.action.value}' is not executable.",
            error=f"Unsupported execution action: {action.action.value}",
        )
