---
name: line-proxy
description: Expert guide for the LINE Proxy MCP Server - Blocking automation, terminal notifications, and history extraction.
version: 3.1.0
tags: [line, mcp, automation, proxy]
---

# LINE Proxy MCP Server

This server provides direct tools to interact with the LINE Chrome Extension via CDP (Port 9222). It is optimized for **Hermes Terminal Notifications**, ensuring proactive feedback for all automated tasks.

## ⚠️ MANDATORY EXECUTION PROTOCOL

**1. Environment Configuration:**
Ensure the following variables are set in `~/.hermes/.env`. See `.env.example` for details:
- `LINE_OWNER_NAME`: Your display name for AI attribution.
- `LINE_DEFAULT_MODEL`: The Gemini model to use.
- `GOOGLE_API_KEY`: Required for AI logic.

**2. Precise Chat Interaction Workflow (The "Ladder" Pattern):**
To avoid sending messages to the wrong group or contact when names are similar, you MUST follow this sequence:
1. **Find**: Call `find_chats(keyword="NAME")` first.
2. **Identify**: Extract the `chat_id` from the correct entry in the results.
3. **Execute**: Pass both `chat_name` AND `chat_id` to subsequent tools (`run_task`, `open_chat`, `send_line_message`, etc.).

**3. Long-Running Task Execution Pattern:**
Always use the `terminal` tool in `background=true` mode. Pass the `chat_id` if available to ensure the engine locks onto the correct room:
```python
terminal(
    command="mcporter call line_proxy.run_task chat_name:\"NAME\" chat_id:\"ID\" task:\"DESCRIPTION\" --timeout 3600000",
    background=true,
    notify_on_complete=true
)
```

**2. Testing & Git Commit Safety Pattern:**
To prevent incomplete test runs and protect Git integrity in Hermes environments, you MUST explicitly declare the timeout. If `TIMEOUT_SET` is missing or below 180, the execution will be blocked.
```python
terminal(
    command="export TIMEOUT_SET=180 && git commit -m '...' --verify",
    timeout=180
)
```

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
- **Profile Overlay Handling**: If clicking a contact opens a **Profile Popup** (common when search results include non-active chats), `select_chat` now automatically detects and clicks the **'Chat'** button to enter the room.
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
- **`find_chats(keyword)`**: 
  - Searches for chats (private or group) matching the keyword.
  - **Returns**: `[{"name": "...", "type": "...", "chat_id": "..."}]`.
  - **Deduplication**: Results are automatically deduplicated by `chat_id`.
- **`open_chat(chat_name, chat_type, chat_id)`**:
  - Navigates to and opens a specific chat.
  - **Precision**: Uses `chat_id` (the `data-mid` attribute) as the primary matching criterion to avoid ambiguity.
- **`get_line_messages(chat_name, limit, chat_id)`**: 
  - **Returns**: `[{"sender": "...", "text": "...", "timestamp": "..."}]`.
  - **Matching**: Uses `chat_id` if provided for precise chat selection.
  - **Sender Identification**: Automatically distinguishes between 'Owner', 'Hermes', and group members.
  - **Timestamp Inheritance**: Clustered messages inherit timestamps from the latest message in the cluster.
  - **Order**: Chronological (Oldest First).

### 3. Messaging
- **`send_line_message(chat_name, text, chat_id)`**: 
  - Sends a message with the `[Hermes]` prefix.
  - Uses `chat_id` for precise selection if provided.

### 4. Session & Login
- **`login_line()`**: 
  - Uses `LINE_EMAIL` and `LINE_PASSWORD` from `.env`.
  - Returns `MFA_CODE_FOUND:XXXXXX` if a verification code is displayed.
  - Automatically polls for 5 minutes for phone verification success.
  - If not logged in, other tools will return an error guiding you to use this tool.

### 5. Interactive Tasks (The "Brain")
- **`run_task(chat_name, task)`**: Synchronous AI-driven task execution. 
  - **WARNING**: Do not call directly. See "MANDATORY EXECUTION PROTOCOL" above.

## Maintenance & Logs
- **Logs**: `~/.line-proxy/logs/{chat_name}.log`
 - **Tests**: `pytest tests/test_chat_navigation.py` (Run within the venv)
