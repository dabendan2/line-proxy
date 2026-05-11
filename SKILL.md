---
name: line-proxy
description: Expert guide for the LINE Proxy MCP Server - Blocking automation, terminal notifications, and history extraction.
version: 3.1.0
tags: [line, mcp, automation, proxy]
---

# LINE Proxy MCP Server

This server provides direct tools to interact with the LINE Chrome Extension via CDP (Port 9222). It is optimized for **Hermes Terminal Notifications**, ensuring proactive feedback for all automated tasks.

## 🛠 Latest Technical Discoveries (May 2026)

### 1. DOM Traversal Quirk: Newest-First
Unlike standard web apps, the LINE Extension's message list often places **Newest messages at the top** of the DOM tree.
- **Impact**: Standard `querySelectorAll` results are in reverse chronological order.
- **Fix**: The `extract_messages` tool automatically reverses the results to ensure the Engine receives the standard **Oldest-First** list (where `msgs[-1]` is the latest).

### 2. Robust Self-Detection
CSS Class names in the Extension are randomized (e.g., `message-module__message__7odk3`).
- **Reliable Indicator**: We now use the `data-direction="reverse"` attribute and `justify-content: flex-end` computed styles to identify messages sent by the user.

### 3. Navigation Integrity
- **Tab Switching**: The `select_chat` tool now automatically switches to the **'CHATS' tab** before searching. This prevents the "Friends" tab from opening a profile overlay instead of the chat window.
- **Pointer Events**: Uses `force=True` on clicks to bypass UI layers that intercept pointer events.

## Core Implementation Pattern: Blocking + Notifications

Always use the `terminal` tool with `background=true` and `notify_on_complete=true` to start long-running tasks. 

```python
terminal(
    command="mcporter call line_proxy.run_task chat_name:\"NAME\" task:\"DESCRIPTION\" --timeout 3600000",
    background=true,
    notify_on_complete=true
)
```

## Tool Reference (MCP)

### 1. Instance Management
- **`prepare_line_instance(port, profile_name)`**: Ensures Chromium is running with the correct profile.

### 2. Chat Navigation & Inspection
- **`find_chat(chat_name)`**: Searches for and opens a chat window. Includes a screenshot.
- **`get_line_messages(chat_name, limit)`**: 
  - **Returns**: `[{"text": "...", "is_self_dom": bool, "timestamp": "..."}]`.
  - **Order**: Chronological (Oldest First).

### 3. Messaging
- **`send_line_message(chat_name, text)`**: Sends a message with the `[Hermes]` prefix.

### 4. Interactive Tasks (The "Brain")
- **`run_task(chat_name, task)`**: Synchronous AI-driven task execution.

## Maintenance & Logs
- **Logs**: `~/.line-proxy/logs/{chat_name}.log`
- **Tests**: `/home/ubuntu/line-proxy/venv/bin/pytest /home/ubuntu/line-proxy/tests/test_order_logic.py`
