"""Tests for MacTools local computer wrappers."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from telegram_agent.tools.mac_tools import MacTools


@pytest.mark.asyncio
async def test_get_system_info_returns_expected_keys(tmp_path: Path):
    tools = MacTools(screenshots_dir=tmp_path)
    info = await tools.get_system_info()
    assert "hostname" in info
    assert "os" in info
    assert "disk_free" in info
    assert info["hostname"]


@pytest.mark.asyncio
async def test_open_url_invokes_open_command(tmp_path: Path):
    tools = MacTools(screenshots_dir=tmp_path)
    with patch("telegram_agent.tools.mac_tools.run_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = (0, "", "")
        ok, msg = await tools.open_url("https://www.google.com", app_name="Google Chrome")

    assert ok is True
    assert "Google Chrome" in msg
    mock_exec.assert_awaited_once_with(
        "open", "-a", "Google Chrome", "https://www.google.com"
    )


@pytest.mark.asyncio
async def test_take_screenshot_verifies_file_creation(tmp_path: Path):
    tools = MacTools(screenshots_dir=tmp_path)

    async def fake_exec(*args, **kwargs):
        # Create a non-empty dummy PNG file at the target path (last arg)
        Path(args[-1]).write_bytes(b"\x89PNG\r\n\x1a\nfakepng")
        return 0, "", ""

    with patch("telegram_agent.tools.mac_tools.run_exec", side_effect=fake_exec):
        ok, path, msg = await tools.take_screenshot()

    assert ok is True
    assert path is not None
    assert Path(path).exists()
    assert "Captured screenshot" in msg
