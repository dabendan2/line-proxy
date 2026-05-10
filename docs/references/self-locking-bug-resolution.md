# Self-Locking Bug Resolution

## Issue
In May 2026, a bug was discovered where `mcporter call line_proxy.run_task` would consistently fail with:
`[LOCK] Another instance (PID XXX) is already monitoring 'chat_name'. Exiting.`

## Root Cause
The `run_task` tool in `mcp_server.py` was calling `lock.acquire()` before spawning `line_proxy.run_task (MCP)` via `subprocess.run`. However, `line_proxy.run_task (MCP)` ALSO called `lock.acquire()` upon startup. Since they both targeted the same chat name, the child process (engine) would see the lock held by the parent (server) and exit immediately.

## Resolution
The redundant lock acquisition was removed from `mcp_server.py`. 
- **Pattern**: The entry-point script that actually performs the long-running loop (`line_proxy.run_task (MCP)`) is responsible for managing the lock. The MCP server acts as a thin wrapper and should not attempt to lock the resource itself.

## Migration Context
The project was also moved from `~/.hermes/scripts/line-proxy` to `~/line-proxy`. All `mcporter` configurations and internal path constants (in `src/config.py`) must reflect the new home directory path to avoid `ENOENT` errors.
