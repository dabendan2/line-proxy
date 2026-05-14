---
name: chat-agent
description: Expert guide for the Chat Agent System - A modular multi-channel messaging automation platform (LINE, etc.).
version: 4.0.0
tags: [chat, automation, ai-agent, mcp, multi-channel]
---

# Chat Agent System

A modular platform for automated communication across multiple channels (LINE, and future integrations like Messenger, Taobao, etc.), driven by a decoupled AI Engine.

## ⚠️ MANDATORY EXECUTION PROTOCOL

**0. Hard Constraints (Strictly Enforced):**
- **NO BYPASS**: Never use `--no-verify` or `-n` with Git. All commits MUST pass tests.
- **TIMEOUT REQUIRED**: Always set `export TIMEOUT_SET=180` (or higher) for any command triggering tests.
- **SSOT**: If a test fails, FIX the code or environment. Do not bypass the safeguard.

**1. Environment Configuration:**
Ensure variables are set in `~/.hermes/.env`:
- `LINE_OWNER_NAME`: Your display name for AI attribution.
- `LINE_DEFAULT_MODEL`: The Gemini model to use.
- `GOOGLE_API_KEY`: Required for AI reasoning.
- Data and logs are stored in `~/.chat-agent/`.

**2. Multi-Channel Architecture:**
- **Core Engine**: `src/core/engine.py` (ChatEngine). Decoupled from UI specifics.
- **Channel Factory**: `src/channels/factory.py`. Central registry for adding/retrieving channels.
- **Channels**: Platform-specific drivers in `src/channels/` (e.g., `line/`, `messenger/`).
- **Abstraction**: All channels must implement the `BaseChannel` interface (`src/channels/base.py`).

**3. Tool Usage via MCP:**
- **Generalized Tools**: `login`, `prepare_instance`, `find_chats`, `open_chat`, `get_messages`, `run_task`.
- **Channel Parameter**: All tools now accept a `channel` argument (defaulting to "line").

**4. Precise Chat Interaction (The "Ladder" Pattern):**
To avoid platform-specific errors, always:
1. **Find**: `find_chats(keyword="NAME", channel="line")`.
2. **Identify**: Extract `chat_id` (e.g., MID for LINE).
3. **Execute**: Pass `chat_name` AND `chat_id` to `run_task` or `open_chat`.

## 🛠 Project Structure

```text
src/
├── core/                # AI reasoning & history management
│   ├── engine.py
│   └── run_engine.py    # Generic engine runner
├── channels/            # Platform implementations
│   ├── base.py          # Abstract BaseChannel interface
│   ├── factory.py       # Channel registry & factory
│   └── line/            # LINE driver implementation
├── utils/               # Shared tools (browser, locker, config)
└── mcp_server.py        # Generalized MCP entry point
```

## 🚀 Core Implementation Patterns

### Long-Running Tasks
Always use `background=true` for automation to prevent timeouts:
```python
terminal(
    command="mcporter call chat_agent.run_task channel:\"line\" chat_name:\"NAME\" chat_id:\"ID\" task:\"TASK\" --timeout 3600000",
    background=true,
    notify_on_complete=true
)
```

## 🧩 Channel Interface (BaseChannel)
Any new channel must implement:
- `select_chat(name, id)`: Navigate to chat.
- `find_chats(keyword)`: Search for chats.
- `open_chat(name, type, id)`: Open specific chat.
- `extract_messages(limit)`: Fetch history.
- `send_message(text)`: Send reply.
- `send_image(path)`: Send media.
- `is_logged_in()`: Check login status.
- `perform_login(email, pwd)`: Handle credentials.

## ログ & メンテナンス (Maintenance)
- **Logs**: `~/.chat-agent/logs/{chat_name}.log`
- **Tests**: `./venv/bin/python run_line_tests.py` (Verify all 59 tests)
