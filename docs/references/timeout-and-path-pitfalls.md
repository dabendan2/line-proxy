# LINE Proxy: Timeout and Path Pitfalls

## 1. Path Migration (ENOENT Errors)
The LINE Proxy was migrated from `~/.hermes/scripts/line-proxy` to `~/line-proxy`. 
If you encounter `ENOENT` when calling `mcporter`, verify the paths in `~/config/mcporter.json`:

```json
{
  "mcpServers": {
    "line_proxy": {
      "command": "/home/ubuntu/line-proxy/venv/bin/python3",
      "args": ["/home/ubuntu/line-proxy/src/mcp_server.py"]
    }
  }
}
```

## 2. Interactive Task Timeouts
`mcporter` has a default call timeout of 60 seconds. This is insufficient for interactive loops (like Tic-Tac-Toe or complex bookings). 
**Fix**: Always append `--timeout 3600000` to the `mcporter call` command when using `run_task`.

## 3. Stale Locks
Locks are stored as `<chat_name>.pid` in `~/.line-proxy/locks/`. 
- **Symptom**: "Error: Chat 'X' is already being managed".
- **Resolution**: 
  1. Check if PID is alive: `ps -p <PID>`.
  2. If stale, `rm ~/.line-proxy/locks/<name>.pid`.

## 4. MCP vs Engine Locking
Do not acquire the lock in `mcp_server.py` before spawning `line_proxy.run_task (MCP)`. If both try to acquire it, the engine will fail because the server held it first. Let the engine handle all stateful locking.
