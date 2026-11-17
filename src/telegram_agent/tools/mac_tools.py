"""Safe macOS command wrappers for approved local computer actions."""

from __future__ import annotations

import asyncio
import os
import platform
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple


async def run_exec(*args: str, timeout: float = 15.0) -> Tuple[int, str, str]:
    """Execute a command without a shell and return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return 124, "", f"Command timed out after {timeout}s"

    return (
        proc.returncode or 0,
        stdout_bytes.decode("utf-8", errors="replace").strip(),
        stderr_bytes.decode("utf-8", errors="replace").strip(),
    )


class MacTools:
    """Encapsulates approved macOS actions and verification probes."""

    def __init__(self, screenshots_dir: Path) -> None:
        self._screenshots_dir = screenshots_dir

    async def open_application(self, app_name: str) -> Tuple[bool, str]:
        """Launch or focus an approved macOS application."""
        code, _, err = await run_exec("open", "-a", app_name)
        if code != 0:
            return False, err or f"Failed to open application '{app_name}'."
        return True, f"Opened application '{app_name}'."

    async def open_url(self, url: str, app_name: str = "Google Chrome") -> Tuple[bool, str]:
        """Open a URL in the specified approved browser."""
        code, _, err = await run_exec("open", "-a", app_name, url)
        if code != 0:
            return False, err or f"Failed to open '{url}' in '{app_name}'."
        return True, f"Opened '{url}' in '{app_name}'."

    async def open_file(self, file_path: str) -> Tuple[bool, str]:
        """Open an existing local file with its default macOS application."""
        resolved = Path(file_path).expanduser().resolve()
        if not resolved.exists():
            return False, f"File not found: {resolved}"
        code, _, err = await run_exec("open", str(resolved))
        if code != 0:
            return False, err or f"Failed to open file: {resolved}"
        return True, f"Opened file '{resolved}'."

    async def take_screenshot(self) -> Tuple[bool, Optional[str], str]:
        """Capture a macOS screenshot silently (-x) to the screenshots directory."""
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        target_path = (self._screenshots_dir / f"screenshot_{timestamp}.png").resolve()

        code, _, err = await run_exec("screencapture", "-x", str(target_path))
        if code != 0:
            return (
                False,
                None,
                err or "screencapture failed (check macOS Screen Recording permissions).",
            )
        if not target_path.exists() or target_path.stat().st_size == 0:
            return False, None, "Screenshot file was not created or is empty."
        return True, str(target_path), f"Captured screenshot: {target_path.name}"

    async def get_system_info(self) -> Dict[str, str]:
        """Retrieve basic non-sensitive Mac system information."""
        code, sw_vers_out, _ = await run_exec("sw_vers")
        os_version = (
            " | ".join(line.strip() for line in sw_vers_out.splitlines())
            if code == 0 and sw_vers_out
            else f"{platform.system()} {platform.release()}"
        )

        _, uptime_out, _ = await run_exec("uptime")
        disk = shutil.disk_usage("/")
        free_gb = disk.free / (1024 ** 3)
        total_gb = disk.total / (1024 ** 3)

        return {
            "hostname": socket.gethostname(),
            "os": os_version,
            "architecture": platform.machine(),
            "user": os.getenv("USER", "unknown"),
            "uptime": uptime_out or "unavailable",
            "disk_free": f"{free_gb:.1f} GB free / {total_gb:.1f} GB total",
        }

    async def is_app_running(self, app_name: str) -> bool:
        """Check whether an application is currently running on macOS."""
        code, _, _ = await run_exec("pgrep", "-ix", app_name)
        if code == 0:
            return True
        code_partial, _, _ = await run_exec("pgrep", "-if", app_name)
        return code_partial == 0
