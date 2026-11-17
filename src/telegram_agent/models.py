"""Shared Pydantic data models for agent communication."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Supported action types proposed by AI reasoning."""

    OPEN_URL = "open_url"
    OPEN_APP = "open_app"
    TAKE_SCREENSHOT = "take_screenshot"
    OPEN_FILE = "open_file"
    SYSTEM_INFO = "system_info"
    CLARIFY = "clarify"
    UNSUPPORTED = "unsupported"


class RiskLevel(str, Enum):
    """Risk classification for proposed actions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class ProposedAction(BaseModel):
    """Structured action proposed by the AI reasoning component."""

    action: ActionType
    application: Optional[str] = None
    url: Optional[str] = None
    target: Optional[str] = None
    file_path: Optional[str] = None
    take_screenshot_after: bool = False
    reason: str = ""
    clarification_question: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PolicyDecision(BaseModel):
    """Result of evaluating a ProposedAction against the safety policy."""

    allowed: bool
    requires_approval: bool
    risk_level: RiskLevel
    reason: str


class ExecutionResult(BaseModel):
    """Outcome of running an approved action on the Mac."""

    success: bool
    action: ActionType
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    screenshot_path: Optional[str] = None
    error: Optional[str] = None


class VerificationResult(BaseModel):
    """Outcome of verifying whether an action actually occurred."""

    verified: bool
    checks: List[str] = Field(default_factory=list)
    evidence_screenshot_path: Optional[str] = None
    failure_reason: Optional[str] = None


class AgentResponse(BaseModel):
    """Final response prepared for Telegram delivery."""

    text: str
    screenshot_path: Optional[str] = None
    requires_approval: bool = False
    approval_id: Optional[str] = None
    is_error: bool = False
