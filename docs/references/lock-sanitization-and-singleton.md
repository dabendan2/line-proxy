# PID Lock Sanitization and Management

The `lock_manager.py` sanitizes chat names before creating lock files in `~/.line-proxy/locks/`.

## Sanitization Rules
- Non-alphanumeric characters (like `.`) are replaced with `_`.
- Example: `dabendan.test` becomes `dabendan_test.pid`.

## Operational Safety
1. **Always verify path**: Check for sanitized names when manually cleaning locks.
2. **Singleton Enforcement**: The system uses `psutil` to verify if the PID in the lock file is actually a running Python/Pytest process.
3. **Stale Lock Recovery**: If the PID is no longer active, the lock is automatically overwritten by the new process.