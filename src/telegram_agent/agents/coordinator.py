"""Coordinator / Instruction Agent: orchestrates reasoning, policy, execution, verification, and response."""

from __future__ import annotations

import logging

from telegram_agent.agents.computer_action import ComputerActionAgent
from telegram_agent.agents.response import ResponseAgent
from telegram_agent.agents.verification import VerificationAgent
from telegram_agent.config import Settings
from telegram_agent.llm.claude_client import ClaudeReasoningClient
from telegram_agent.models import ActionType, AgentResponse, ProposedAction
from telegram_agent.safety.approval import PendingApprovalManager
from telegram_agent.safety.policy import evaluate_policy

logger = logging.getLogger(__name__)


class CoordinatorAgent:
    """Central workflow coordinator for natural-language Telegram requests."""

    def __init__(
        self,
        settings: Settings,
        reasoning_client: ClaudeReasoningClient,
        action_agent: ComputerActionAgent,
        verification_agent: VerificationAgent,
        response_agent: ResponseAgent,
        approval_manager: PendingApprovalManager,
    ) -> None:
        self._settings = settings
        self._reasoning = reasoning_client
        self._action_agent = action_agent
        self._verification_agent = verification_agent
        self._response_agent = response_agent
        self._approvals = approval_manager

    async def handle_message(
        self, user_id: int, chat_id: int, message: str
    ) -> AgentResponse:
        """Process an authorized user's natural-language message end-to-end."""
        proposed = await self._reasoning.interpret(message)
        logger.info(
            "Interpreted action=%s confidence=%.2f",
            proposed.action.value,
            proposed.confidence,
        )

        if proposed.action == ActionType.CLARIFY:
            return self._response_agent.format_clarification(proposed)

        if proposed.action == ActionType.UNSUPPORTED:
            return self._response_agent.format_unsupported(proposed)

        decision = evaluate_policy(proposed, self._settings)
        if not decision.allowed:
            return self._response_agent.format_policy_blocked(decision)

        if decision.requires_approval:
            pending = self._approvals.create(
                user_id=user_id,
                chat_id=chat_id,
                action=proposed,
                original_message=message,
            )
            return self._response_agent.format_approval_request(
                approval_id=pending.approval_id,
                action=proposed,
                decision=decision,
            )

        return await self.execute_approved_action(proposed)

    async def execute_approved_action(self, action: ProposedAction) -> AgentResponse:
        """Execute an action that has passed policy/approval, verify it, and format response."""
        execution = await self._action_agent.execute(action)
        verification = await self._verification_agent.verify(action, execution)
        return self._response_agent.format_outcome(action, execution, verification)
