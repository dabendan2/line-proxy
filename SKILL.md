---
name: chat-agent
description: Expert guide for the Chat Agent System - A modular multi-channel messaging automation platform (LINE, etc.).
version: 4.0.0
tags: [chat, automation, ai-agent, mcp, multi-channel]
---

# Chat Agent System

A modular platform for automated communication across multiple channels (LINE, and future integrations like Messenger, Taobao, etc.), driven by a decoupled AI Engine.

## ⚠️ MANDATORY EXECUTION PROTOCOL

**1. Environment Configuration:**
Ensure variables are set in `~/.hermes/.env`:
- `LINE_OWNER_NAME`: Your display name for AI attribution.
- `LINE_DEFAULT_MODEL`: The Gemini model to use.
- `GOOGLE_API_KEY`: Required for AI reasoning.
- Data and logs are stored in `~/.chat-agent/`.

**2. Multi-Channel Architecture:**
- **Core Engine**: `src/core/engine.py` (ChatEngine). It is decoupled from UI specifics.
- **Channels**: Platform-specific drivers in `src/channels/`.
- **Abstraction**: All channels must implement the `BaseChannel` interface (`src/core/base_channel.py`).

**3. Precise Chat Interaction (The "Ladder" Pattern):**
To avoid platform-specific errors, always:
1. **Find**: `find_chats(keyword="NAME")`.
2. **Identify**: Extract `chat_id` (e.g., MID for LINE).
3. **Execute**: Pass `chat_name` AND `chat_id` to `run_task` or `open_chat`.

## 🛠 Project Structure

```text
src/
├── core/                # AI reasoning & history management
├── channels/            # Platform implementations (e.g., line/)
├── utils/               # Shared tools (browser, locker, config)
└── mcp_server.py        # Unified MCP entry point
```

## 🚀 Core Implementation Patterns

### Long-Running Tasks
Always use `background=true` for automation to prevent timeouts:
```python
terminal(
    command="mcporter call line_proxy.run_task chat_name:\"NAME\" chat_id:\"ID\" task:\"TASK\" --timeout 3600000",
    background=true,
    notify_on_complete=true
)
```

### Testing Safety
Explicitly declare timeout for Git/Tests:
```bash
export TIMEOUT_SET=180 && npm test
```

## 🧩 Channel Interface (BaseChannel)
Any new channel must implement:
- `select_chat(name, id)`: Navigate to chat.
- `extract_messages(limit)`: Fetch history.
- `send_message(text)`: Send reply.
- `send_image(path)`: Send media.

## ログ & メンテナンス (Maintenance)
- **Logs**: `~/.chat-agent/logs/{chat_name}.log`
- **Tests**: `./venv/bin/python run_line_tests.py` (Verify all 59 tests)
