"""Claude natural-language reasoning client for interpreting user requests."""

from __future__ import annotations

import json
import logging
from typing import Any, FrozenSet, Optional

import anthropic

from telegram_agent.models import ActionType, ProposedAction

logger = logging.getLogger(__name__)

PROPOSE_ACTION_TOOL = {
    "name": "propose_action",
    "description": (
        "Propose a single structured computer action (or clarification/unsupported) "
        "based on the user's natural-language instruction."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [e.value for e in ActionType],
                "description": "The type of action to perform.",
            },
            "application": {
                "type": "string",
                "description": "Approved macOS application name (e.g., 'Google Chrome', 'Safari', 'Finder').",
            },
            "url": {
                "type": "string",
                "description": "Full http:// or https:// URL when action is 'open_url'.",
            },
            "target": {
                "type": "string",
                "description": "Human-readable target name (e.g., 'Google').",
            },
            "file_path": {
                "type": "string",
                "description": "Local file path when action is 'open_file'.",
            },
            "take_screenshot_after": {
                "type": "boolean",
                "description": "True if the user also asked for a screenshot after the main action.",
            },
            "reason": {
                "type": "string",
                "description": "Brief explanation of why this action was chosen.",
            },
            "clarification_question": {
                "type": "string",
                "description": "Question to ask the user when action is 'clarify'.",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Confidence score from 0.0 to 1.0.",
            },
        },
        "required": ["action", "reason", "confidence"],
    },
}


def build_system_prompt(approved_apps: FrozenSet[str]) -> str:
    """Build the system prompt instructing Claude on safe structured action proposal."""
    apps_list = ", ".join(sorted(approved_apps))
    return (
        "You are the AI reasoning component of a Mac Telegram AI Agent.\n"
        "Your job is to interpret the user's natural-language request and call the "
        "`propose_action` tool with a structured action.\n\n"
        f"Approved applications on this Mac: {apps_list}.\n\n"
        "Supported actions:\n"
        "- open_url: Open an http/https URL in an approved browser (default: Google Chrome).\n"
        "- open_app: Open an approved macOS application.\n"
        "- take_screenshot: Capture a screenshot of the Mac screen.\n"
        "- open_file: Open a specific local file path.\n"
        "- system_info: Retrieve basic Mac system information (OS, hostname, uptime, disk, memory).\n"
        "- clarify: Ask the user a concise clarification question if the request is ambiguous.\n"
        "- unsupported: Use when the user asks for something dangerous, destructive "
        "(deleting files, running arbitrary shell commands, changing system settings), or unsupported.\n\n"
        "Rules:\n"
        "1. Never guess when an instruction is ambiguous — use action='clarify'.\n"
        "2. If the user asks to open a website AND take a screenshot (e.g. 'Open Google in Chrome "
        "and take a screenshot'), use action='open_url' and set take_screenshot_after=true.\n"
        "3. Always include full https:// URLs for well-known sites (e.g. Google -> https://www.google.com).\n"
        "4. You do not execute anything yourself; you only propose the structured action."
    )


class ClaudeReasoningClient:
    """Wrapper around Anthropic's async client to interpret natural-language requests."""

    def __init__(
        self,
        api_key: str,
        model: str,
        approved_apps: FrozenSet[str],
        client: Optional[Any] = None,
    ) -> None:
        self._model = model
        self._system_prompt = build_system_prompt(approved_apps)
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key)

    async def interpret(self, user_message: str) -> ProposedAction:
        """Interpret a natural-language user message into a ProposedAction."""
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=self._system_prompt,
            tools=[PROPOSE_ACTION_TOOL],
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": user_message}],
        )
        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: Any) -> ProposedAction:
        for block in getattr(response, "content", []):
            if getattr(block, "type", None) == "tool_use" and block.name == "propose_action":
                return ProposedAction.model_validate(block.input)
            if getattr(block, "type", None) == "text":
                try:
                    data = json.loads(block.text)
                    return ProposedAction.model_validate(data)
                except Exception:
                    continue

        logger.warning("Claude response did not contain a valid propose_action tool call.")
        return ProposedAction(
            action=ActionType.CLARIFY,
            reason="Could not parse a structured action from the model response.",
            clarification_question="I couldn't clearly understand that request. Could you rephrase what you'd like me to do on the Mac?",
            confidence=0.0,
        )
