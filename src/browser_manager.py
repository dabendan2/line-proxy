import os
import subprocess
import time
import psutil
from pathlib import Path
from typing import Optional, Dict, Any

class BrowserManager:
    def __init__(self, port: int = 9222, profile_name: str = "line_booking_session") -> None:
        self.port = port
        self.profile_name = profile_name
        self.user_data_dir = Path.home() / "snap/chromium/common" / profile_name
        self.ext_id = "ophjlpahpchlmihnnnihgmmeilfjmjjc"
        # Adjusted path to match May 2026 Snap configuration
        self.ext_path = Path.home() / "snap/chromium/common/chromium/Default/Extensions" / self.ext_id / "3.7.2_0"

    def is_port_in_use(self) -> Optional[int]:
        for conn in psutil.net_connections():
            if conn.laddr.port == self.port and conn.status == 'LISTEN':
                return conn.pid
        return None

    def check_singleton_lock(self) -> Optional[int]:
        lock_file = self.user_data_dir / "SingletonLock"
        if lock_file.is_symlink():
            lock_info = os.readlink(str(lock_file))
            try:
                # Format: ip-address-pid
                lock_pid = int(lock_info.split('-')[-1])
                if psutil.pid_exists(lock_pid):
                    return lock_pid
            except (ValueError, IndexError):
                pass
            # Stale lock
            lock_file.unlink()
        return None

    def prepare_instance(self) -> Dict[str, Any]:
        # 1. Active CDP & Profile Assertion
        try:
            import httpx
            response = httpx.get(f"http://localhost:{self.port}/json", timeout=2)
            if response.status_code == 200:
                # Port is active, but is it the CORRECT profile?
                occupied_pid = self.is_port_in_use()
                if occupied_pid:
                    proc = psutil.Process(occupied_pid)
                    cmdline = " ".join(proc.cmdline())
                    if str(self.user_data_dir) in cmdline:
                        # Correct profile is running
                        pages = response.json()
                        if any(self.ext_id in p.get("url", "") for p in pages):
                            return {"status": "success", "port": self.port, "cdp_url": f"http://localhost:{self.port}"}
                        return {"status": "success", "message": "Correct browser instance up, extension page navigation may be needed.", "port": self.port}
                    else:
                        # WRONG PROFILE! We must kill it to resolve the port collision
                        print(f"Port {self.port} occupied by WRONG profile. Terminating PID {occupied_pid}...")
                        proc.terminate()
                        proc.wait(timeout=5)
                else:
                    # Port is active but PID not found via psutil (rare)? Fall through to full cleanup
                    pass
        except Exception:
            pass

        # 2. Zombie / Stale Port Cleanup
        # If the port is in use but step 1 failed, it's a zombie or another app.
        occupied_pid = self.is_port_in_use()
        if occupied_pid:
            try:
                proc = psutil.Process(occupied_pid)
                if "chrome" in proc.name().lower() or "chromium" in proc.name().lower():
                    print(f"Cleaning up zombie chrome process (PID {occupied_pid}) on port {self.port}...")
                    proc.terminate()
                    proc.wait(timeout=5)
                else:
                    return {"status": "error", "message": f"Port {self.port} occupied by foreign process: {proc.name()}"}
            except Exception as e:
                return {"status": "error", "message": f"Port {self.port} blocked and cleanup failed: {str(e)}"}

        # 3. Singleton Lock Recovery
        active_pid = self.check_singleton_lock()
        if active_pid:
            # If we reached here, the port check failed, so the process holding the lock is a zombie
            try:
                proc = psutil.Process(active_pid)
                print(f"Terminating process {active_pid} holding stale lock on {self.user_data_dir}...")
                proc.terminate()
                proc.wait(timeout=5)
            except:
                pass
            
            # Force unlink stale lock
            lock_file = self.user_data_dir / "SingletonLock"
            if lock_file.exists(): lock_file.unlink()

        # 4. Create Dirs and Launch
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "xvfb-run", "-a", "-s", "-screen 0 1600x1000x24",
            "chromium-browser",
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.user_data_dir}",
            "--no-sandbox",
            f"--disable-extensions-except={self.ext_path}",
            f"--load-extension={self.ext_path}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-dev-shm-usage",
            f"chrome-extension://{self.ext_id}/index.html"
        ]
        
        log_file = Path.home() / ".line-proxy" / "logs" / "browser_startup.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a") as f:
            f.write(f"\n--- Browser Launch at {time.ctime()} ---\n")
            subprocess.Popen(cmd, stdout=f, stderr=f)

        # 5. Wait for readiness
        max_retries = 15
        for i in range(max_retries):
            try:
                import httpx
                response = httpx.get(f"http://localhost:{self.port}/json", timeout=2)
                if response.status_code == 200:
                    pages = response.json()
                    if any(self.ext_id in p.get("url", "") for p in pages):
                        return {"status": "success", "port": self.port, "cdp_url": f"http://localhost:{self.port}"}
                    return {"status": "success", "message": "Browser up, but extension page may need navigation.", "port": self.port}
            except Exception:
                pass
            time.sleep(2)
            
        return {"status": "error", "message": "Browser failed to start within timeout"}

if __name__ == "__main__":
    bm = BrowserManager(port=9222)
    print(bm.prepare_instance())
