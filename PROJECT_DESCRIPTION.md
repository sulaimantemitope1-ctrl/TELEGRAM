# Telegram AI Agent

## Project Overview

The Telegram AI Agent is an agentic AI solution that allows an authorized user to communicate with and perform approved actions on a Mac computer through a Telegram chatbot.

The user interacts with the system from the Telegram application on their phone using normal, natural-language instructions. The solution runs on the user's Mac and connects Telegram, an AI reasoning model, and local computer tools.

For example, the user could send:

**“Open Google in Chrome.”**

or:

**“Take a screenshot and send it to me.”**

The system should understand the request, determine what action is required, perform the approved action on the Mac, verify that the action occurred, and send the result back to the user through Telegram.

---

## Business / User Problem

People often need to interact with their computers while they are away from the keyboard or using another device.

Traditional remote-control tools normally require the user to navigate the computer interface manually.

This project explores a different approach: allowing a user to communicate with their computer conversationally through Telegram.

Instead of navigating menus, the user can describe what they want in natural language and allow an AI-enabled workflow to coordinate the appropriate approved computer action.

---

## Project Goal

The goal is to build a working prototype that demonstrates communication between:

**Phone → Telegram → Telegram Bot API → Mac application → AI reasoning → computer tools → verification → Telegram response**

The system should allow an authorized Telegram user to:

- Send commands from a phone.
- Communicate with a Python application running on a Mac.
- Use natural language rather than only fixed commands.
- Have AI interpret the user's request.
- Perform approved computer actions.
- Verify whether the requested action occurred.
- Receive confirmation, screenshots, or other results through Telegram.
- Require human approval for sensitive or potentially dangerous actions.

---

## Example User Journey

The user sends the following message through Telegram:

**“Open Google in Chrome and take a screenshot.”**

The system should:

1. Receive the Telegram message.
2. Confirm that the Telegram user is authorized.
3. Send the natural-language request to the AI reasoning component.
4. Interpret the requested actions.
5. Determine that Chrome should be opened.
6. Navigate to Google.
7. Capture a screenshot.
8. Verify that the actions were completed.
9. Send the screenshot or confirmation back to the user through Telegram.

---

# Agent Architecture

The prototype will use coordinated agents or specialized components.

## 1. Coordinator / Instruction Agent

The Coordinator receives the user's Telegram request and manages the overall workflow.

It determines:

- What the user is asking for.
- Whether the request is supported.
- Which agent or tool should act next.
- Whether human approval is required.

The Coordinator should not guess when a request is unclear.

---

## 2. Computer Action Agent

The Computer Action Agent performs approved actions on the Mac.

Possible actions include:

- Opening an approved application.
- Opening Chrome or another browser.
- Opening a website.
- Taking a screenshot.
- Opening a file.
- Retrieving basic computer information.

The agent should only perform actions explicitly approved by the system's rules.

---

## 3. Verification Agent

The Verification Agent checks whether the requested action actually occurred.

For example, after opening a website, it can confirm that the action completed and capture a screenshot as evidence.

The agent must not report success if the action cannot be verified.

---

## 4. Response Agent

The Response Agent communicates the final result back to the user through Telegram.

It may return:

- A confirmation message.
- A failure message.
- A request for clarification.
- A screenshot.
- Other approved output produced by the computer.

---

# Human Approval and Safety

The human user remains in control of the system.

Low-risk actions may be completed automatically when appropriate.

Potentially destructive, sensitive, or high-risk actions should require explicit human approval before execution.

The system must:

- Never silently execute destructive actions.
- Never guess when an instruction is ambiguous.
- Never claim an action succeeded if it failed.
- Restrict computer control to authorized Telegram users.
- Ask the user for clarification when necessary.

---

# Technologies and Services

## Google Antigravity

Google Antigravity will be used as the primary development environment for creating, testing, and refining the prototype.

## Python

Python will be used to implement the application, agent coordination, Telegram communication, AI integration, computer actions, and tests.

## Telegram Bot API

The Telegram Bot API will allow the Python application running on the Mac to receive messages from and send messages to the user's Telegram chatbot.

## Anthropic API / Claude

The Anthropic API will provide access to Claude.

Claude will act as the natural-language reasoning component responsible for interpreting what the user wants and converting the request into an approved structured action.

For example:

**User message:**  
“Open Google in Chrome.”

**Possible AI interpretation:**

- Action: Open URL
- Application: Chrome
- Target: Google
- URL: https://www.google.com

The AI reasoning component does not directly control the computer. It proposes the action, while the local computer tools perform approved actions.

## Git / GitHub

Git will be used to maintain version history throughout development.

GitHub may be used to store or share the project repository if required.

Sensitive credentials must never be committed to Git or GitHub.

---

# Credentials and Configuration

The project requires the following private configuration values:

- **Telegram Bot Token** - allows the Python application to communicate with the Telegram bot.
- **Anthropic API Key** - allows the application to send natural-language requests to Claude.
- **Claude Model ID** - identifies which Claude model the application should use.
- **Authorized Telegram User ID** - restricts control of the Mac to an approved Telegram user.
- **GitHub Personal Access Token (optional)** - may be used for authenticated GitHub operations over HTTPS or through the GitHub API when needed.

## Private `.env` File

The real credentials must be stored only in a private `.env` file on the local computer.

Example structure:

```env
TELEGRAM_BOT_TOKEN=your_real_telegram_bot_token
ANTHROPIC_API_KEY=your_real_anthropic_api_key
CLAUDE_MODEL=your_claude_model_id
ALLOWED_TELEGRAM_USER_IDS=your_telegram_numeric_user_id
GITHUB_TOKEN=your_github_personal_access_token
REQUIRE_APPROVAL_FOR_DANGEROUS=true
ALWAYS_REQUIRE_APPROVAL=false
```

The values above are placeholders. Real API keys and tokens must not be written into this project description.

## `.env.example`

The repository should also contain a safe `.env.example` file using placeholders:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-sonnet-5-5
ALLOWED_TELEGRAM_USER_IDS=123456789
GITHUB_TOKEN=your_github_personal_access_token_here
REQUIRE_APPROVAL_FOR_DANGEROUS=true
ALWAYS_REQUIRE_APPROVAL=false
```

## Secret Protection

The `.env` file must be excluded from Git through `.gitignore`.

API keys and tokens must not appear in:

- Git commits
- GitHub repositories
- screenshots
- project documentation
- logs
- assignment evidence

The project documentation should show only the variable names and placeholder values, while the actual credentials remain private on the local Mac.

---

# Development Approach

The project will be developed incrementally.

## Milestone 1: Telegram Communication

Establish communication between Telegram on the user's phone and the Python application running on the Mac.

Tests:

- `/start`
- `/myid`

Success means the Mac application can receive a Telegram message and send a response back to the phone.

## Milestone 2: AI Reasoning

Connect the application to the Anthropic API.

The user should be able to send a natural-language instruction such as:

**“Open Google in Chrome.”**

Claude should interpret the request and return a structured proposed action.

At this stage, the computer action does not need to execute yet.

## Milestone 3: Computer Actions

Connect approved local computer tools.

The system should be able to perform actions such as:

- Opening Chrome.
- Opening a website.
- Opening an approved application.

## Milestone 4: Verification

Verify that the requested computer action occurred.

The system should be able to capture evidence such as a screenshot.

## Milestone 5: Return Results to Telegram

Send the result of the computer action back to the user.

Example:

**Phone → “Take a screenshot” → Mac captures screenshot → screenshot returns to Telegram**

## Milestone 6: Human Approval and Guardrails

Test actions that should require human confirmation.

Ensure unauthorized Telegram users cannot control the computer.

---

# Testing Strategy

The solution should be tested one component at a time.

### Test 1: Telegram Connection

Send `/start`.

Expected result: the bot responds.

### Test 2: User Identification

Send `/myid`.

Expected result: the bot returns the Telegram user's numeric ID.

### Test 3: Authorized User

Add the user's numeric Telegram ID to the authorized-user configuration.

Expected result: the authorized user can use the system while unauthorized users are rejected.

### Test 4: AI Interpretation

Send:

**“Open Google in Chrome.”**

Expected result: Claude correctly identifies the intended computer action.

### Test 5: Computer Execution

Send an approved browser instruction.

Expected result: Chrome opens on the Mac.

### Test 6: Screenshot

Send:

**“Take a screenshot.”**

Expected result: the Mac captures a screenshot.

### Test 7: Return Result

Expected result: the screenshot or confirmation is sent back to the Telegram chat.

---

# Evidence

Evidence should be collected throughout development.

Examples include:

- Antigravity project screenshots.
- Telegram `/start` response.
- Telegram `/myid` response.
- AI interpretation of a natural-language instruction.
- Browser opening on the Mac.
- Screenshot returned through Telegram.
- Automated test results.
- Git commit history.
- Human approval checkpoint.
- Error-handling examples.

Screenshots containing API keys, bot tokens, or other credentials must not be included.

---

# Definition of Success

The prototype will be considered successful when an authorized user can send a natural-language request from Telegram on a phone, have the request interpreted by the AI reasoning component, have an approved action performed on the Mac, verify the result, and receive the result back through Telegram.

The completed workflow should demonstrate:

**Telegram communication + AI reasoning + agent coordination + computer action + verification + human control.**

This prototype is intended to demonstrate the architecture and feasibility of an agentic AI solution rather than a production-ready remote administration system.
