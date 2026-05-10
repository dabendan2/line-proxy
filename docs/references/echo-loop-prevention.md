# 防止 LINE Self-chat 模式下的回音循環 (Echo Loop Prevention)

在處理 LINE Extension 的個人對話 (Self-chat, 如 LINE Keep 或與自己的對話) 時，AI 發出的訊息在 DOM 結構上會與「對方發來的訊息」完全一致。若識別不精確，AI 會看到自己剛發出的話並誤以為是新訊息，進而無限循環。

## 核心解決方案：嚴格身分識別 (Strict Identity)

### 1. 訊息清理 (Message Sanitization)
LINE 網頁版會在訊息泡泡周圍加上「已讀 (Read)」狀態與時間戳記（如 `5:50 AM`）。在進行身分比對前，必須使用正規表達式將這些雜訊剔除。

```python
import re

def sanitize(text):
    # 移除 "Read" 以及常見的時間格式 (如 5:50 AM, 10:12 PM)
    text = re.sub(r'Read\s*\d{1,2}:\d{2}\s*(AM|PM)?', '', text, flags=re.IGNORECASE).strip()
    # 正規化空白字元，防止跨平台渲染差異導致比對失敗
    text = re.sub(r'\s+', ' ', text)
    return text
```

### 2. 嚴格字串比對 (Strict Comparison)
絕對禁止使用 `in` (包含) 邏輯，因為使用者的短回覆（如「5」）可能剛好包含在 AI 之前的長回覆中。必須使用完全一致的比對：

```python
def is_hermes_msg(self, dom_text):
    clean_dom = sanitize(dom_text)
    for sent in self.state.get("sent_messages", []):
        if clean_dom == sanitize(sent):
            return True
    return False
```

### 3. 日誌優先 (Log-First Persistence)
日誌 (`~/.line-proxy/logs/*.db.txt`) 是區分自他身分的唯一單一事實來源。
- **嚴禁清理日誌**：重啟腳本時，必須讀取舊日誌來恢復 `SENT:` 紀錄清單。
- **即時同步**：發送訊息後，必須立即將該訊息加入 `sent_messages` 並更新 `last_processed_msg`。

## 分流輸出協定 ([RESULT] Partitioning)
為了確保 AI 的「任務進度報告」不外流給人類使用者，採用分流解析邏輯：

1. LLM 生成包含 `[RESULT]` 的回覆。
2. 腳本截斷 `[RESULT]` 之前的文字發送至 LINE。
3. 腳本擷取 `[RESULT]` 及其之後的內容輸出至終端機，並優雅退出。

這能有效解決「AI 向使用者報告自己正在等待」的尷尬情況。
