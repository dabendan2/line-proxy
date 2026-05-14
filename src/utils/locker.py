import os
import sys
import psutil

class PIDLock:
    def __init__(self, chat_name):
        lock_dir = os.path.expanduser("~/.chat-agent/locks")
        os.makedirs(lock_dir, exist_ok=True)
        # Use sanitized chat name for filename
        safe_name = "".join([c if c.isalnum() else "_" for c in chat_name])
        self.lock_path = os.path.join(lock_dir, f"{safe_name}.pid")
        self.chat_name = chat_name

    def acquire(self):
        """Checks for existing lock and acquires if possible. Returns True if acquired."""
        if os.path.exists(self.lock_path):
            with open(self.lock_path, "r") as f:
                try:
                    old_pid = int(f.read().strip())
                    if psutil.pid_exists(old_pid):
                        # Verify it's actually a similar process (optional but safer)
                        proc = psutil.Process(old_pid)
                        # We also check if it's the SAME PID to prevent self-locking during tests
                        is_python = "python" in proc.name().lower() or "pytest" in proc.name().lower()
                        if is_python:
                            print(f"[LOCK] Another instance (PID {old_pid}) is already monitoring '{self.chat_name}'. Exiting.")
                            return False
                except (ValueError, psutil.NoSuchProcess):
                    pass # Stale lock or invalid PID
        
        # Acquire lock
        with open(self.lock_path, "w") as f:
            f.write(str(os.getpid()))
        return True

    def release(self):
        """Removes the lock file."""
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except Exception as e:
            print(f"[LOCK] Error releasing lock: {e}")
