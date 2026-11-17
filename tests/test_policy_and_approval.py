"""Tests for safety policy evaluation and human approval manager."""

from telegram_agent.config import Settings
from telegram_agent.models import ActionType, ProposedAction, RiskLevel
from telegram_agent.safety.approval import PendingApprovalManager
from telegram_agent.safety.policy import evaluate_policy


def _settings(always_approve: bool = False, require_dangerous: bool = True) -> Settings:
    return Settings(
        telegram_bot_token="token",
        anthropic_api_key="key",
        allowed_telegram_user_ids=frozenset({123}),
        always_require_approval=always_approve,
        require_approval_for_dangerous=require_dangerous,
    )


def test_open_google_in_chrome_is_low_risk_and_allowed():
    action = ProposedAction(
        action=ActionType.OPEN_URL,
        application="chrome",
        url="https://www.google.com",
        reason="Open Google",
    )
    decision = evaluate_policy(action, _settings())
    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.risk_level == RiskLevel.LOW


def test_unapproved_app_is_blocked():
    action = ProposedAction(
        action=ActionType.OPEN_APP,
        application="UnknownDangerousApp",
        reason="Open unknown app",
    )
    decision = evaluate_policy(action, _settings())
    assert decision.allowed is False
    assert decision.risk_level == RiskLevel.BLOCKED


def test_invalid_url_scheme_is_blocked():
    action = ProposedAction(
        action=ActionType.OPEN_URL,
        application="Google Chrome",
        url="file:///etc/passwd",
        reason="Open local file via URL",
    )
    decision = evaluate_policy(action, _settings())
    assert decision.allowed is False
    assert decision.risk_level == RiskLevel.BLOCKED


def test_sensitive_app_terminal_requires_approval():
    action = ProposedAction(
        action=ActionType.OPEN_APP,
        application="Terminal",
        reason="Open Terminal",
    )
    decision = evaluate_policy(action, _settings(require_dangerous=True))
    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.risk_level == RiskLevel.HIGH


def test_always_require_approval_flag():
    action = ProposedAction(
        action=ActionType.TAKE_SCREENSHOT,
        reason="Take screenshot",
    )
    decision = evaluate_policy(action, _settings(always_approve=True))
    assert decision.allowed is True
    assert decision.requires_approval is True


def test_sensitive_system_path_blocked_for_open_file():
    action = ProposedAction(
        action=ActionType.OPEN_FILE,
        file_path="/etc/hosts",
        reason="Open hosts file",
    )
    decision = evaluate_policy(action, _settings())
    assert decision.allowed is False
    assert decision.risk_level == RiskLevel.BLOCKED


def test_pending_approval_owner_and_single_use():
    manager = PendingApprovalManager(ttl_seconds=60)
    action = ProposedAction(action=ActionType.OPEN_APP, application="Terminal")
    pending = manager.create(
        user_id=123, chat_id=123, action=action, original_message="Open Terminal"
    )

    # Wrong user cannot pop
    assert manager.pop_for_user(pending.approval_id, user_id=999) is None

    # Correct user pops once
    popped = manager.pop_for_user(pending.approval_id, user_id=123)
    assert popped is not None
    assert popped.action.application == "Terminal"

    # Second pop returns None
    assert manager.pop_for_user(pending.approval_id, user_id=123) is None
