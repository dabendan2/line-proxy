import os
import subprocess
import time
import psutil
from pathlib import Path

class BrowserManager:
    def __init__(self, port=9222, profile_name="line_booking_session"):
        self.port = port
        self.profile_name = profile_name
        self.user_data_dir = Path.home() / "snap/chromium/common" / profile_name
        self.ext_id = "ophjlpahpchlmihnnnihgmmeilfjmjjc"
        # Adjusted path to match start_line_snap.sh pattern
        self.ext_path = Path.home() / "snap/chromium/common/chromium/Default/Extensions" / self.ext_id / "3.7.2_0"

    def is_port_in_use(self):
        for conn in psutil.net_connections():
            if conn.laddr.port == self.port and conn.status == 'LISTEN':
                return conn.pid
        return None

    def check_singleton_lock(self):
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

    def prepare_instance(self):
        # 1. Check Port
        occupied_pid = self.is_port_in_use()
        if occupied_pid:
            return {"status": "error", "message": f"Port {self.port} occupied by PID {occupied_pid}"}

        # 2. Check Lock
        active_pid = self.check_singleton_lock()
        if active_pid:
            return {"status": "error", "message": f"Profile locked by active PID {active_pid}"}

        # 3. Create Dirs
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        # 4. Launch via xvfb-run
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
        
        # Start in background
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 5. Wait for readiness
        max_retries = 15
        for i in range(max_retries):
            try:
                import httpx
                response = httpx.get(f"http://localhost:{self.port}/json/version", timeout=2)
                if response.status_code == 200:
                    return {"status": "success", "port": self.port, "cdp_url": f"http://localhost:{self.port}"}
            except Exception:
                pass
            time.sleep(2)
            
        return {"status": "error", "message": "Browser failed to start within timeout"}

if __name__ == "__main__":
    bm = BrowserManager(port=9222)
    print(bm.prepare_instance())
