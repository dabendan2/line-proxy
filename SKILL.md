---
name: line-proxy
description: Expert guide for the LINE Proxy MCP Server - Async automation, fast messaging, and history extraction.
version: 2.0.0
tags: [line, mcp, automation, proxy]
---

# LINE Proxy MCP Server

This server provides direct tools to interact with the LINE Chrome Extension via CDP (Port 9222). It supports both lightweight messaging and full-autonomous AI proxy tasks in the background.

## Tool Reference (MCP)

### 1. Instance Management
- **`prepare_line_instance(port, profile_name)`**:
  - Ensures Chromium is running with the correct profile.
  - Handles singleton locks.
  - **Usage**: Call this first if the browser is not running.

### 2. Chat Navigation & Inspection
- **`find_chat(chat_name)`**:
  - Searches for and opens a chat window.
  - Takes a screenshot for visual confirmation.
- **`get_line_messages(chat_name, limit)`**:
  - **Primary tool for reading context.**
  - Returns a JSON list of recent messages: `[{"text": "...", "is_self_dom": bool, "timestamp": "..."}]`.
  - Much faster and more accurate than OCR/Vision.

### 3. Messaging
- **`send_line_message(chat_name, text)`**:
  - **Lightweight & Fast**.
  - Automatically adds the `[Hermes]` prefix.
  - Use this for simple replies or status updates.

### 4. Autonomous Background Tasks
- **`start_proxy_task(chat_name, task)`**:
  - **Asynchronous (Non-blocking)**.
  - Spawns a background engine (`run_engine.py`) to manage a complex conversation.
  - Returns a `PID` immediately.
  - Use this for tasks that may take minutes or hours (e.g., restaurant bookings).
- **`get_task_status(chat_name)`**:
  - Checks if the background engine is still running.
  - Returns the last 10 lines of the task log.

## Best Practices

### Context Handling
- Always use `get_line_messages` to verify the state before sending a message.
- The extraction returns messages in **chronological order** (Oldest First). The latest message is at the end of the list.

### Background Task Lifecycle
1. Start with `start_proxy_task`.
2. The agent turn ends immediately.
3. Check progress later using `get_task_status`.
4. Logs are stored at `~/.line-proxy/logs/{chat_name}.log`.

### Manual CLI Usage
For debugging or manual intervention:
```bash
# Start an autonomous task manually
/home/ubuntu/line-proxy/venv/bin/python3 /home/ubuntu/line-proxy/src/run_engine.py --chat "Target" --task "Goal"
```

## Maintenance
Run tests to verify functionality:
```bash
/home/ubuntu/line-proxy/venv/bin/pytest /home/ubuntu/line-proxy/tests/test_mcp_server.py
```
