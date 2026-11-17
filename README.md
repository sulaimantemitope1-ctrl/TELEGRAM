# Telegram AI Agent

A prototype agentic AI solution that allows an authorized user to control approved actions on a Mac through a Telegram bot using natural language, powered by the Telegram Bot API, Anthropic's Claude, and local macOS tools.

## Architecture

1. **Coordinator Agent** (`src/telegram_agent/agents/coordinator.py`): Orchestrates natural-language interpretation via Claude, safety policy checks, human-approval checkpoints, execution, and verification.
2. **Computer Action Agent** (`src/telegram_agent/agents/computer_action.py`): Executes approved actions on macOS (`open -a`, `screencapture -x`, system info) via `MacTools`.
3. **Verification Agent** (`src/telegram_agent/agents/verification.py`): Confirms that actions occurred (running process checks, non-empty screenshot verification) before reporting success.
4. **Response Agent** (`src/telegram_agent/agents/response.py`): Formats confirmations, failures, clarification prompts, approval requests, and screenshot attachments for Telegram.

## Setup

1. Create and activate the virtual environment (already created at `.venv` if set up locally):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your real credentials:

   ```bash
   cp .env.example .env
   ```

   Required variables:
   - `TELEGRAM_BOT_TOKEN`: Token from `@BotFather`.
   - `ANTHROPIC_API_KEY`: Your Anthropic API key.
   - `CLAUDE_MODEL`: Claude model ID (e.g., `claude-sonnet-4-20250514`).
   - `ALLOWED_TELEGRAM_USER_IDS`: Comma-separated numeric Telegram user IDs (use `/myid` in the bot to find yours).

   > **Note:** On macOS, grant **Screen Recording** permission to your terminal/IDE if you want the bot to capture screenshots with `screencapture`.

## Running the Bot

```bash
PYTHONPATH=src .venv/bin/python -m telegram_agent.main
```

## Running Tests

```bash
.venv/bin/pytest -v
```
