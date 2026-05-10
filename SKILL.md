---
name: line-proxy
description: Expert guide for the LINE Proxy MCP Server - Blocking automation, terminal notifications, and history extraction.
version: 3.0.0
tags: [line, mcp, automation, proxy]
---

# LINE Proxy MCP Server

This server provides direct tools to interact with the LINE Chrome Extension via CDP (Port 9222). It is optimized for **Hermes Terminal Notifications**, ensuring proactive feedback for all automated tasks.

## Core Implementation Pattern: Blocking + Notifications

The LINE Proxy has been refactored to use a **Blocking Tool Pattern**. This allows the Hermes Agent system to natively handle backgrounding and auto-notifications.

### Standard Calling Convention
Always use the `terminal` tool with `background=true` and `notify_on_complete=true` to start long-running tasks:

```python
terminal(
    command="npx mcporter call line_proxy.run_task chat_name:\"NAME\" task:\"DESCRIPTION\"",
    background=true,
    notify_on_complete=true
)
```

**Why?**
- **Proactive Feedback**: Hermes will automatically alert you via Telegram/Messaging when the task finishes.
- **Log Capture**: The task's output (including final board states or booking confirmations) is captured natively.
- **Simplified Lifecycle**: No need to manually poll PIDs or logs.

## Tool Reference (MCP)

### 1. Instance Management
- **`prepare_line_instance(port, profile_name)`**:
  - Ensures Chromium is running with the correct profile and extension.
  - Call this first if the browser is not active.

### 2. Chat Navigation & Inspection
- **`find_chat(chat_name)`**:
  - Searches for and opens a chat window.
  - Takes a screenshot for visual confirmation.
- **`get_line_messages(chat_name, limit)`**:
  - **Primary tool for reading context.**
  - Returns a JSON list of recent messages: `[{"text": "...", "is_self_dom": bool, "timestamp": "..."}]`.
  - The list is **chronological (Oldest First)**. The latest message is `msgs[-1]`.

### 3. Messaging
- **`send_line_message(chat_name, text)`**:
  - Lightweight and fast.
  - Automatically adds the `[Hermes]` prefix.
  - Use for one-off replies or status updates.

### 4. Interactive Tasks (The "Brain")
- **`run_task(chat_name, task)`**:
  - **Synchronous (Blocking)**.
  - Blocks until the AI engine completes the task (e.g., win/loss, booking confirmed, or exit).
  - Returns a final report including stdout/stderr.
  - **Mandatory**: Must be called via the `terminal` background pattern described above.

## Redirection & Documentation Links

The following skills are now integrated and should follow this central documentation:
- `line-agent-proxy-orchestration`: High-level logic and etiquette.
- `line-automation`: General LINE strategies.
- `line-extension-automation`: Technical CDP/Shadow-DOM details.

## Maintenance & Logs
- **Logs**: `~/.line-proxy/logs/{chat_name}.log` (contains detailed engine thought processes).
- **Tests**: `/home/ubuntu/line-proxy/venv/bin/pytest /home/ubuntu/line-proxy/tests/`
