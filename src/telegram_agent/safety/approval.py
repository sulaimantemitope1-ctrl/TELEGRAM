"""In-memory store for pending human-approval requests."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from telegram_agent.models import ProposedAction


@dataclass
class PendingApproval:
    """Represents an action waiting for explicit user confirmation."""

    approval_id: str
    user_id: int
    chat_id: int
    action: ProposedAction
    original_message: str
    created_at: float = field(default_factory=time.time)


class PendingApprovalManager:
    """Manages pending approvals with TTL expiration and user ownership checks."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl_seconds = ttl_seconds
        self._pending: Dict[str, PendingApproval] = {}

    def create(
        self,
        user_id: int,
        chat_id: int,
        action: ProposedAction,
        original_message: str,
    ) -> PendingApproval:
        """Create and store a new pending approval."""
        self._purge_expired()
        approval_id = uuid.uuid4().hex[:12]
        entry = PendingApproval(
            approval_id=approval_id,
            user_id=user_id,
            chat_id=chat_id,
            action=action,
            original_message=original_message,
        )
        self._pending[approval_id] = entry
        return entry

    def pop_for_user(
        self, approval_id: str, user_id: int
    ) -> Optional[PendingApproval]:
        """Retrieve and remove a pending approval if valid, unexpired, and owned by user_id."""
        self._purge_expired()
        entry = self._pending.get(approval_id)
        if entry is None or entry.user_id != user_id:
            return None
        return self._pending.pop(approval_id)

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [
            key
            for key, item in self._pending.items()
            if now - item.created_at > self._ttl_seconds
        ]
        for key in expired:
            del self._pending[key]
