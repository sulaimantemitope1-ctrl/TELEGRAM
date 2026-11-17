"""Telegram user authorization checks."""

from __future__ import annotations

from typing import FrozenSet, Optional


def is_user_authorized(
    user_id: Optional[int], allowed_user_ids: FrozenSet[int]
) -> bool:
    """Return True only when user_id is present and in the configured allowlist."""
    if user_id is None or not allowed_user_ids:
        return False
    return user_id in allowed_user_ids
