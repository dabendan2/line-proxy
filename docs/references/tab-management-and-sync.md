# LINE 擴充功能分頁與同步管理 (Tab Management & Sync)

在自動化 LINE Chrome Extension 時，網頁分頁的管理直接影響訊息同步的可靠性。

## 1. Websocket 競爭 (Sync Contention)
- **現象**：當同一個 Chrome Profile 下開啟多個 LINE 擴充功能頁面（`chrome-extension://.../index.html`）時，LINE 的 Websocket 連線會發生競爭。
- **後果**：新收到的訊息會隨機出現在其中一個分頁，導致其他分頁（包括代理人正在監控的那個）看起來沒有即時更新，造成代理人「視而不見」。

## 2. 登入持久化風險 (Login Persistence)
- **現象**：關閉「最後一個」LINE 活動分頁時，擴充功能可能會判定 Session 結束並強制登出。
- **對策**：執行清理腳本時，**必須確保保留至少一個**活動中的 LINE 分頁，嚴禁將其全數關閉（除非目的是重啟瀏覽器環境）。

## 3. 清理策略 (Cleanup Strategy)
- **自動巡檢**：代理人啟動前或定期（如每小時）執行 `scripts/cleanup_line_tabs.py`。
- **邏輯**：
  1. 列出所有 URL 包含 `chrome-extension://ophjlpahpchlmihnnnihgmmeilfjmjjc/` 的頁面。
  2. 關閉所有 `chrome-error://` 或 `about:blank` 的無效頁面。
  3. 若 LINE 分頁數量 > 1，保留第一個，關閉其餘所有分頁。
