# Synchronous MCP Task with Terminal Notifications (Preferred Pattern)

While traditional MCP patterns suggest non-blocking background processes for long tasks, Hermes-integrated agents benefit more from a **Blocking Tool + Terminal Background** architecture. This ensures that the agent system can natively monitor process exit and notify the user.

## Preferred Architectural Pattern

1. **Blocking MCP Tool (`run_task`)**:
   - Performs the logic synchronously.
   - Blocks until completion or failure.
   - Outputs a final report to `stdout`.

2. **Hermes Terminal Execution**:
   - The agent calls the MCP tool via the `terminal` tool.
   - **Flags**: `background=true` and `notify_on_complete=true`.
   - **Result**: Hermes handles the backgrounding, PID tracking, and **auto-notifies** the user when the process finishes.

### Comparison

| Feature | Non-blocking MCP | Blocking MCP + Terminal |
|---------|------------------|-------------------------|
| Complexity | High (custom PIDs/Logs) | Low (native Hermes logic) |
| Notification | Manual Polling Required | **Automatic via Hermes** |
| Log Capture | Manual file reading | Native in terminal output |
| Timeouts | Bypassed by detaching | Handled by terminal backend |

### Implementation Guide

To start a long-running LINE Proxy task:
```python
terminal(
    command="npx mcporter call line_proxy.run_task chat_name:\"NAME\" task:\"DESCRIPTION\"",
    background=true,
    notify_on_complete=true
)
```
This ensures the agent will proactively tell the user "Task Complete" as soon as the game or process ends.
