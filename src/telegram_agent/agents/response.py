"""Response Agent: formats verified results, errors, and prompts for Telegram."""

from __future__ import annotations

from telegram_agent.models import (
    ActionType,
    AgentResponse,
    ExecutionResult,
    PolicyDecision,
    ProposedAction,
    VerificationResult,
)


class ResponseAgent:
    """Formats structured agent outcomes into clear Telegram responses."""

    def format_clarification(self, action: ProposedAction) -> AgentResponse:
        question = (
            action.clarification_question
            or "Could you clarify what you would like me to do on the Mac?"
        )
        return AgentResponse(text=f"Clarification needed:\n{question}")

    def format_unsupported(self, action: ProposedAction) -> AgentResponse:
        reason = action.reason or "That request is not supported by this agent."
        return AgentResponse(
            text=f"Request not supported:\n{reason}",
            is_error=True,
        )

    def format_policy_blocked(self, decision: PolicyDecision) -> AgentResponse:
        return AgentResponse(
            text=f"Blocked by safety policy:\n{decision.reason}",
            is_error=True,
        )

    def format_approval_request(
        self,
        approval_id: str,
        action: ProposedAction,
        decision: PolicyDecision,
    ) -> AgentResponse:
        target_parts = []
        if action.application:
            target_parts.append(f"App: {action.application}")
        if action.url:
            target_parts.append(f"URL: {action.url}")
        if action.file_path:
            target_parts.append(f"File: {action.file_path}")
        details_line = " | ".join(target_parts) if target_parts else action.action.value

        text = (
            f"Approval required (Risk: {decision.risk_level.value.upper()})\n"
            f"Action: {action.action.value}\n"
            f"Details: {details_line}\n"
            f"Reason: {decision.reason}\n\n"
            "Please confirm whether to proceed."
        )
        return AgentResponse(
            text=text,
            requires_approval=True,
            approval_id=approval_id,
        )

    def format_outcome(
        self,
        action: ProposedAction,
        execution: ExecutionResult,
        verification: VerificationResult,
    ) -> AgentResponse:
        if not execution.success or not verification.verified:
            reason = (
                verification.failure_reason
                or execution.error
                or "The action could not be verified."
            )
            return AgentResponse(
                text=f"Action failed or could not be verified:\n{reason}",
                is_error=True,
            )

        lines = [f"Done: {execution.summary}"]
        if action.action == ActionType.SYSTEM_INFO and execution.details:
            lines.append("")
            for key, value in execution.details.items():
                label = key.replace("_", " ").title()
                lines.append(f"- {label}: {value}")

        if verification.checks:
            lines.append("")
            lines.append("Verification:")
            for check in verification.checks:
                lines.append(f"- {check}")

        return AgentResponse(
            text="\n".join(lines),
            screenshot_path=verification.evidence_screenshot_path,
        )
