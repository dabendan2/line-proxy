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


## Technical References (Consolidated)

### From lock-mechanism-implementation.md
# PID 鎖定機制實作 (Lock Mechanism Implementation)

為了防止單一 LINE 聊天室有多個代理人實例 (Instances) 同時運行並導致「重複發訊」或「競態條件 (Race Condition)」，必須實作文件鎖定。

## 1. 核心邏輯
- **鎖定標的**：鎖定檔案以 `chat_name` 為名（例如 `dabendan_test.pid`），存放於 `~/.line-proxy/locks/`。
- **原子性檢查**：
  1. 嘗試讀取已存在的 `.pid` 檔案。
  2. 使用 `psutil.pid_exists(old_pid)` 檢查該進程是否還在。
  3. 若進程存在且名稱包含 `python`，則新實例必須**立即終止**並報錯。
  4. 若進程不存在（Stale Lock），則刪除舊檔並建立新檔，寫入當前 PID。

## 2. Python 實作範例 (`lock_manager.py`)
```python
import os, psutil

class PIDLock:
    def __init__(self, chat_name):
        self.lock_path = os.path.expanduser(f"~/.line-proxy/locks/{chat_name}.pid")
        
    def acquire(self):
        if os.path.exists(self.lock_path):
            with open(self.lock_path, "r") as f:
                try:
                    old_pid = int(f.read().strip())
                    if psutil.pid_exists(old_pid) and "python" in psutil.Process(old_pid).name().lower():
                        return False
                except: pass
        with open(self.lock_path, "w") as f:
            f.write(str(os.getpid()))
        return True

    def release(self):
        if os.path.exists(self.lock_path):
            os.remove(self.lock_path)
```

## 3. 恢復策略 (Recovery)
- **手動清理**：若自動恢復失敗，使用者可執行 `pkill -f line_proxy.run_task (MCP)` 並手動刪除 `~/.line-proxy/locks/` 下的所有檔案。
- **自動化集成**：`line_proxy.run_task (MCP)` 的啟動腳本應在 `main` 函數最前端呼叫 `acquire()`，並在 `finally` 塊呼叫 `release()`。


### From path-migration-troubleshooting.md
# LINE Proxy Path Migration & ENOENT Troubleshooting

## Context
In May 2026, the `line-proxy` project was moved from the hermes-internal directory (`~/.hermes/scripts/line-proxy`) to the home directory (`~/line-proxy`) for better visibility and management.

## Symptom
`mcporter` fails with an `ENOENT` error when calling `line_proxy` tools:
```
[mcporter] line_proxy appears offline (spawn /home/ubuntu/.hermes/scripts/line-proxy/venv/bin/python3 ENOENT).
Error: spawn /home/ubuntu/.hermes/scripts/line-proxy/venv/bin/python3 ENOENT
```

## Diagnosis
The `mcporter` configuration is pointing to the old path. `mcporter` might be reading from multiple locations:
1. `~/line-proxy/config/mcporter.json`
2. `~/config/mcporter.json`

## Fix
1. Locate the active `mcporter.json` (e.g., `find ~ -name "mcporter.json"`).
2. Update the `command` and `args` paths to use the new `~/line-proxy/` prefix.
3. Verify with `mcporter list --json` to ensure the transport path is correct.


### From mcp-server-setup-and-timeouts.md
# MCP Server Setup & Timeout Management

## 1. Installation on Externally Managed Environments
In environments where `pip install` is blocked by PEP 668 (e.g., modern Ubuntu/Debian), use the `--break-system-packages` flag for the `mcp` SDK if a virtual environment is not feasible for the global agent:
```bash
pip install mcp --break-system-packages
```

## 2. Ad-hoc Configuration with mcporter
To use the `line-proxy` MCP server without restarting the Hermes Agent (required for `config.yaml` updates), register it with `mcporter`:
```bash
mcporter config add line_proxy \
  --command "/home/ubuntu/line-proxy/venv/bin/python3" \
  --arg "/home/ubuntu/line-proxy/src/mcp_server.py"
```
Call tools via:
```bash
mcporter call line_proxy.prepare_line_instance --config /home/ubuntu/line-proxy/config/mcporter.json
```

## 3. Handling start_proxy_task Timeouts
The `start_proxy_task` tool runs a multi-turn agent loop which frequently exceeds the default 60s MCP/Terminal timeout.
- **Symptom**: `[Command timed out after 60s]` or `mcporter` returning an empty response.
- **Workaround**: If the task is simple (e.g., "send hello"), use a direct Playwright script instead of the full Proxy Engine to avoid the overhead.
- **Reference Script**: `/tmp/send_line_hello.py` (or similar ad-hoc scripts) can bypass the engine for one-off actions.

## 4. Model Availability Pitfalls
The `google-genai` SDK used in the engine defaults to specific model strings. If you see `404 NOT_FOUND` for models like `gemini-2.0-flash-exp` in logs:
1. Verify the model name via `ListModels` in the Google AI Studio console.
2. Ensure the `GOOGLE_API_KEY` is correctly propagated in the MCP server's environment.
3. Use `gemini-1.5-flash` or current stable versions; avoid experimental strings that may be deprecated or moved between API versions (v1 vs v1beta).

## 📚 Documentation Index (Links)
Refer to these files for deep technical patterns and case studies.

### Technical References (`docs/references/`)
- [bank-transaction-retrieval.md](docs/references/bank-transaction-retrieval.md)
- [behavior-consistency-rules.md](docs/references/behavior-consistency-rules.md)
- [behavioral-logic-test-patterns.md](docs/references/behavioral-logic-test-patterns.md)
- [behavioral-safety-patterns.md](docs/references/behavioral-safety-patterns.md)
- [ctbc-extraction-case-study.md](docs/references/ctbc-extraction-case-study.md)
- [ctbc-line-patterns.md](docs/references/ctbc-line-patterns.md)
- [dabendan-test-search-case.md](docs/references/dabendan-test-search-case.md)
- [dom-chronology-and-reversing.md](docs/references/dom-chronology-and-reversing.md)
- [echo-loop-prevention.md](docs/references/echo-loop-prevention.md)
- [etiquette-violation-case-study.md](docs/references/etiquette-violation-case-study.md)
- [full-context-memory-reconstruction.md](docs/references/full-context-memory-reconstruction.md)
- [game-bot-pitfalls.md](docs/references/game-bot-pitfalls.md)
- [gemini-sdk-model-availability.md](docs/references/gemini-sdk-model-availability.md)
- [husky-anti-skip.md](docs/references/husky-anti-skip.md)
- [identity-verification-vision.md](docs/references/identity-verification-vision.md)
- [incremental-disclosure-pattern.md](docs/references/incremental-disclosure-pattern.md)
- [infinite-loop-index-bug.md](docs/references/infinite-loop-index-bug.md)
- [line-1a2b-bot-pattern.md](docs/references/line-1a2b-bot-pattern.md)
- [line-extension-config.md](docs/references/line-extension-config.md)
- [line-hangman-bot-pattern.md](docs/references/line-hangman-bot-pattern.md)
- [line-mfa-handling.md](docs/references/line-mfa-handling.md)
- [line-mfa-troubleshooting.md](docs/references/line-mfa-troubleshooting.md)
- [line-simulation-pitfalls.md](docs/references/line-simulation-pitfalls.md)
- [lock-mechanism-implementation.md](docs/references/lock-mechanism-implementation.md)
- [lock-sanitization-and-singleton.md](docs/references/lock-sanitization-and-singleton.md)
- [log-as-state-architecture.md](docs/references/log-as-state-architecture.md)
- [login-flow-diagnostics.md](docs/references/login-flow-diagnostics.md)
- [mcp-background-task-pattern.md](docs/references/mcp-background-task-pattern.md)
- [mcp-initialization-pattern.md](docs/references/mcp-initialization-pattern.md)
- [mcp-server-setup-and-timeouts.md](docs/references/mcp-server-setup-and-timeouts.md)
- [mcp-transition.md](docs/references/mcp-transition.md)
- [mcp-troubleshooting-diagnostics.md](docs/references/mcp-troubleshooting-diagnostics.md)
- [message-formatting-and-prefix-protocol.md](docs/references/message-formatting-and-prefix-protocol.md)
- [model-config-and-log-debugging.md](docs/references/model-config-and-log-debugging.md)
- [path-migration-troubleshooting.md](docs/references/path-migration-troubleshooting.md)
- [pc-verification-modal.md](docs/references/pc-verification-modal.md)
- [proactive-initiation-and-closures.md](docs/references/proactive-initiation-and-closures.md)
- [redundancy-prevention-patterns.md](docs/references/redundancy-prevention-patterns.md)
- [restaurant-booking-pattern.md](docs/references/restaurant-booking-pattern.md)
- [result-reporting-protocol.md](docs/references/result-reporting-protocol.md)
- [robust-chat-selection-pattern.md](docs/references/robust-chat-selection-pattern.md)
- [sdk-model-availability-pitfalls.md](docs/references/sdk-model-availability-pitfalls.md)
- [self-chat-automation-pitfalls.md](docs/references/self-chat-automation-pitfalls.md)
- [self-chat-detection-nuances.md](docs/references/self-chat-detection-nuances.md)
- [self-chat-identity-extraction.md](docs/references/self-chat-identity-extraction.md)
- [self-chat-identity-reliability.md](docs/references/self-chat-identity-reliability.md)
- [self-locking-bug-resolution.md](docs/references/self-locking-bug-resolution.md)
- [session-case-study-info-dump-failure.md](docs/references/session-case-study-info-dump-failure.md)
- [shell-quoting-pitfalls.md](docs/references/shell-quoting-pitfalls.md)
- [snap-chromium-apparmor.md](docs/references/snap-chromium-apparmor.md)
- [snap-singleton-locks.md](docs/references/snap-singleton-locks.md)
- [startup-takeover-deadlock.md](docs/references/startup-takeover-deadlock.md)
- [strict-alignment-and-clean-slate.md](docs/references/strict-alignment-and-clean-slate.md)
- [tab-management-and-sync.md](docs/references/tab-management-and-sync.md)
- [timeout-and-path-pitfalls.md](docs/references/timeout-and-path-pitfalls.md)

### Code Templates (`docs/templates/`)
- [engine_genai_v2.py](docs/templates/engine_genai_v2.py)
- [etiquette.md](docs/templates/etiquette.md)
- [intelligent_proxy_v15.py](docs/templates/intelligent_proxy_v15.py)
- [line_game_loop.py](docs/templates/line_game_loop.py)
- [line_proxy_template_v2.py](docs/templates/line_proxy_template_v2.py)
- [package.json](docs/templates/package.json)
- [persistent_negotiation_monitor.py](docs/templates/persistent_negotiation_monitor.py)
- [stateful_negotiation_monitor.py](docs/templates/stateful_negotiation_monitor.py)
- [stateful_resilient_proxy.py](docs/templates/stateful_resilient_proxy.py)
- [test_behavior_consistency.py](docs/templates/test_behavior_consistency.py)
- [test_dump_prevention.py](docs/templates/test_dump_prevention.py)

### Archive (`docs/archive/`)
- [Legacy Skill Snapshots](docs/archive/)
