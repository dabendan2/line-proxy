import os
import sys
import psutil
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Cleanup LINE Proxy locks and processes")
    parser.add_argument("--chat", required=True, help="Target contact name")
    parser.add_argument("--clear-log", action="store_true", help="Also delete the log file")
    args = parser.parse_args()

    safe_name = "".join([c if c.isalnum() else "_" for c in args.chat])
    lock_path = Path.home() / ".line-proxy" / "locks" / f"{safe_name}.pid"
    log_path = Path.home() / ".line-proxy" / "logs" / f"{args.chat}.log"

    # 1. Kill Process if lock exists
    if lock_path.exists():
        try:
            with open(lock_path, "r") as f:
                pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    if "python" in proc.name().lower():
                        print(f"Terminating process {pid} for chat '{args.chat}'...")
                        proc.kill()
                    else:
                        print(f"PID {pid} found but doesn't look like a python process. Skipping kill.")
        except Exception as e:
            print(f"Error reading lock file: {e}")
        
        # 2. Remove Lock File
        os.remove(lock_path)
        print(f"Removed lock: {lock_path}")

    # 3. Handle stray processes by CMD match (backup)
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = " ".join(proc.info['cmdline'] or [])
            if "run.py" in cmdline and args.chat in cmdline:
                print(f"Found stray process {proc.info['pid']} matching chat name. Killing...")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 4. Clear Log (Optional)
    if args.clear_log and log_path.exists():
        os.remove(log_path)
        print(f"Deleted log: {log_path}")

    print("Cleanup complete.")

if __name__ == "__main__":
    main()
