# [RESULT] 回報協議與日誌持久化規範

## 1. [RESULT] 回報協議 (Result Reporting Protocol)
子代理人 (Sub-agent) 在執行任務時，必須將「對外溝通」與「對內報告」嚴格分離。

- **對外溝通 (LINE Channel)**：僅發送與人類用戶對話所需的訊息（遵循 `etiquette.md`）。
- **對內報告 (Terminal Output)**：當需要回報任務進度、正在等待回覆、或任務完成時，必須使用 `[END]` 標籤。

### 操作規範：
1. **觸發條件**：
   - 任務達成 (Success)。
   - 進入長時間等待 (Waiting for user)。
   - 遇到無法處理的錯誤 (Error)。
2. **標籤格式**：`[END, reason="(原因)", report="(內容)"]`
3. **原因與計時 (Reason & Wait Time)**：
   - `consulting`: 缺失資訊，需向俊羽請示。 (腳本守候 2 分鐘)
   - `accomplished`: 任務圓滿達成，但未道別。 (腳本守候 5 分鐘)
   - `goodbye`: 任務完成且已正式道別。 (腳本守候 2 分鐘)
4. **終止邏輯**：輸出 `[RESULT]` (或偵測到 `[END]` 標籤) 後，腳本執行最後的守候計時，隨後安全退出。
4. **優點**：
   - 避免「任務報告」污染對話視窗。
   - 主代理人能即時獲取結構化回報並轉達給使用者。

---

## 2. 日誌持久化規範 (Log Persistence)
日誌是子代理人唯一的「長期記憶」與「身分證」。

- **持久路徑**：`~/.line-proxy/logs/` (預設為 `*.db.txt`)。
- **嚴禁刪除**：除非使用者明確要求，否則絕對禁止執行 `rm`, `truncate` 或 `touch` 重置日誌。
- **身分識別核心**：
  - 啟動時必須掃描日誌末端的 `SENT:` 標記。
  - 若最後一則訊息為 `SENT`，則腳本進入靜默等待。
  - 若最後一則為 `NEW MSG` 且無對應 `SENT`，則立即啟動回覆程序。

---

## 3. DOM 訊息清理 (DOM Sanitization)
LINE 網頁版會在訊息文字中夾雜中繼資料。在比對「這是不是我說過的」時，必須預先清理：

```python
import re
def sanitize(text):
    # 過濾 "Read" 與時間戳記 (例如 "5:50 AM", "10:12 PM")
    return re.sub(r'Read\s*\d{1,2}:\d{2}\s*(AM|PM)?', '', text, flags=re.IGNORECASE).strip()
```
