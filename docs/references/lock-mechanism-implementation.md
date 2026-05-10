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
