"""Safety policy evaluation for proposed computer actions."""

from __future__ import annotations

from pathlib import Path
from typing import FrozenSet
from urllib.parse import urlparse

from telegram_agent.config import Settings
from telegram_agent.models import (
    ActionType,
    PolicyDecision,
    ProposedAction,
    RiskLevel,
)

# Common aliases mapped to canonical macOS application names.
APP_ALIASES = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "safari": "Safari",
    "finder": "Finder",
    "notes": "Notes",
    "calculator": "Calculator",
    "terminal": "Terminal",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "textedit": "TextEdit",
    "preview": "Preview",
}

SENSITIVE_APPS: FrozenSet[str] = frozenset({"Terminal"})
SENSITIVE_PATH_PREFIXES = (
    "/System",
    "/Library",
    "/etc",
    "/private/etc",
    "/bin",
    "/sbin",
    "/usr",
    "/var",
    "/private/var",
)


def normalize_app_name(name: str, approved_apps: FrozenSet[str]) -> str:
    """Resolve common aliases to canonical approved app names when possible."""
    cleaned = name.strip()
    lowered = cleaned.lower()
    if lowered in APP_ALIASES:
        canonical = APP_ALIASES[lowered]
        if canonical in approved_apps:
            return canonical
    for approved in approved_apps:
        if approved.lower() == lowered:
            return approved
    return cleaned


def is_valid_http_url(url: str) -> bool:
    """Allow only http/https URLs with a non-empty network location."""
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_safe_file_path(file_path: str) -> bool:
    """Ensure file path does not target sensitive OS directories or contain null bytes."""
    if not file_path or "\x00" in file_path:
        return False
    resolved = str(Path(file_path).expanduser().resolve())
    for prefix in SENSITIVE_PATH_PREFIXES:
        if resolved == prefix or resolved.startswith(prefix + "/"):
            return False
    return True


def evaluate_policy(action: ProposedAction, settings: Settings) -> PolicyDecision:
    """Evaluate whether a proposed action is allowed and requires human approval."""
    if action.action in {ActionType.CLARIFY, ActionType.UNSUPPORTED}:
        return PolicyDecision(
            allowed=True,
            requires_approval=False,
            risk_level=RiskLevel.LOW,
            reason="No computer action will be executed.",
        )

    if action.action in {ActionType.SYSTEM_INFO, ActionType.TAKE_SCREENSHOT}:
        requires_approval = settings.always_require_approval
        return PolicyDecision(
            allowed=True,
            requires_approval=requires_approval,
            risk_level=RiskLevel.LOW,
            reason="Read-only local inspection action.",
        )

    if action.action == ActionType.OPEN_APP:
        if not action.application:
            return PolicyDecision(
                allowed=False,
                requires_approval=False,
                risk_level=RiskLevel.BLOCKED,
                reason="No application name was specified.",
            )
        canonical_app = normalize_app_name(action.application, settings.approved_apps)
        if canonical_app not in settings.approved_apps:
            return PolicyDecision(
                allowed=False,
                requires_approval=False,
                risk_level=RiskLevel.BLOCKED,
                reason=f"Application '{action.application}' is not in the approved apps list.",
            )
        is_sensitive = canonical_app in SENSITIVE_APPS
        risk = RiskLevel.HIGH if is_sensitive else RiskLevel.LOW
        requires_approval = settings.always_require_approval or (
            is_sensitive and settings.require_approval_for_dangerous
        )
        return PolicyDecision(
            allowed=True,
            requires_approval=requires_approval,
            risk_level=risk,
            reason=f"Opening approved application '{canonical_app}'.",
        )

    if action.action == ActionType.OPEN_URL:
        if not action.url or not is_valid_http_url(action.url):
            return PolicyDecision(
                allowed=False,
                requires_approval=False,
                risk_level=RiskLevel.BLOCKED,
                reason="URL must be a valid http:// or https:// address.",
            )
        app_name = normalize_app_name(
            action.application or "Google Chrome", settings.approved_apps
        )
        if app_name not in settings.approved_apps:
            return PolicyDecision(
                allowed=False,
                requires_approval=False,
                risk_level=RiskLevel.BLOCKED,
                reason=f"Browser '{app_name}' is not in the approved apps list.",
            )
        return PolicyDecision(
            allowed=True,
            requires_approval=settings.always_require_approval,
            risk_level=RiskLevel.LOW,
            reason=f"Opening approved URL in '{app_name}'.",
        )

    if action.action == ActionType.OPEN_FILE:
        if not action.file_path or not is_safe_file_path(action.file_path):
            return PolicyDecision(
                allowed=False,
                requires_approval=False,
                risk_level=RiskLevel.BLOCKED,
                reason="File path is missing or points to a restricted system directory.",
            )
        requires_approval = (
            settings.always_require_approval or settings.require_approval_for_dangerous
        )
        return PolicyDecision(
            allowed=True,
            requires_approval=requires_approval,
            risk_level=RiskLevel.MEDIUM,
            reason="Opening a local file requires explicit human confirmation.",
        )

    return PolicyDecision(
        allowed=False,
        requires_approval=False,
        risk_level=RiskLevel.BLOCKED,
        reason=f"Unsupported or blocked action: {action.action}",
    )
