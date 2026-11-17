"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import FrozenSet, Optional

from dotenv import load_dotenv

DEFAULT_APPROVED_APPS: FrozenSet[str] = frozenset(
    {
        "Google Chrome",
        "Safari",
        "Finder",
        "Notes",
        "Calculator",
        "Terminal",
        "Visual Studio Code",
        "TextEdit",
        "Preview",
    }
)


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_user_ids(value: Optional[str]) -> FrozenSet[int]:
    if not value:
        return frozenset()
    ids = set()
    for part in value.split(","):
        cleaned = part.strip()
        if cleaned:
            try:
                ids.add(int(cleaned))
            except ValueError as exc:
                raise ValueError(
                    f"Invalid Telegram user ID in ALLOWED_TELEGRAM_USER_IDS: {cleaned!r}"
                ) from exc
    return frozenset(ids)


def _parse_approved_apps(value: Optional[str]) -> FrozenSet[str]:
    if not value:
        return DEFAULT_APPROVED_APPS
    apps = {part.strip() for part in value.split(",") if part.strip()}
    return frozenset(apps) if apps else DEFAULT_APPROVED_APPS


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    telegram_bot_token: str
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"
    allowed_telegram_user_ids: FrozenSet[int] = field(default_factory=frozenset)
    require_approval_for_dangerous: bool = True
    always_require_approval: bool = False
    approved_apps: FrozenSet[str] = DEFAULT_APPROVED_APPS
    screenshots_dir: Path = field(default_factory=lambda: Path("screenshots"))
    approval_timeout_seconds: int = 300

    @classmethod
    def from_env(cls, env_path: Optional[Path] = None) -> "Settings":
        """Load settings from a .env file (if present) and environment variables."""
        if env_path is not None:
            load_dotenv(dotenv_path=env_path, override=False)
        else:
            load_dotenv(override=False)

        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514").strip()
        if claude_model.startswith("CLAUDE_MODEL="):
            claude_model = claude_model.split("=", 1)[1].strip()
        allowed_ids = _parse_user_ids(os.getenv("ALLOWED_TELEGRAM_USER_IDS"))
        require_dangerous = _parse_bool(
            os.getenv("REQUIRE_APPROVAL_FOR_DANGEROUS"), default=True
        )
        always_approve = _parse_bool(
            os.getenv("ALWAYS_REQUIRE_APPROVAL"), default=False
        )
        approved_apps = _parse_approved_apps(os.getenv("APPROVED_APPS"))
        screenshots_dir = Path(os.getenv("SCREENSHOTS_DIR", "screenshots"))

        return cls(
            telegram_bot_token=telegram_bot_token,
            anthropic_api_key=anthropic_api_key,
            claude_model=claude_model,
            allowed_telegram_user_ids=allowed_ids,
            require_approval_for_dangerous=require_dangerous,
            always_require_approval=always_approve,
            approved_apps=approved_apps,
            screenshots_dir=screenshots_dir,
        )

    def validate_for_runtime(self) -> None:
        """Validate that required credentials are present before starting the bot."""
        missing = []
        if not self.telegram_bot_token or self.telegram_bot_token.startswith("your_"):
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.anthropic_api_key or self.anthropic_api_key.startswith("your_"):
            missing.append("ANTHROPIC_API_KEY")
        if missing:
            raise ValueError(
                "Missing required configuration in .env: " + ", ".join(missing)
            )
