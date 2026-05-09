---
name: line-proxy
description: 基於 LINE Chrome Extension 的強健 AI 代理人系統，支援上下文保留與智慧接管。
tags: [line, proxy, automation]
---

# LINE 代理人引擎 (LINE Proxy Engine)

這是一套強健的 AI 驅動代理系統，旨在代表使用者處理 LINE 對話。具備精準的身分偵測、持久化狀態管理與自動化測試機制。

## 核心特性
- **智慧接管 (Smart Takeover)**：啟動時自動判斷對話末端是否需要回覆，避免在重啟時產生多餘的打招呼或重複自我介紹。
- **身分識別 (Identity Awareness)**：優先解析本地日誌 (`/tmp/line_proxy_*.log`)，在 LINE Keep 或個人對話等發言標籤混亂的環境下，也能精確區分「自己」與「對方」。
- **上下文過濾 (Context Filtering)**：透過 `--last-ignored-msg` 定義任務的「歷史邊界」。
- **日誌即狀態 (Log-as-State)**：完全移除對 JSON 狀態檔的依賴，所有記憶、進度與計時器皆從日誌中即時恢復。

## 檔案結構
- `run.py`: CLI 執行入口。
- `engine.py`: 核心邏輯、Gemini API 調用與狀態恢復引擎。
- `line_utils.py`: 基於 Playwright 的 LINE DOM 操作工具。
- `etiquette.md`: 社交禮儀規範與任務邊界定義。
- `tests/`: 針對接管邏輯的單元測試套件。

## 參數指南：如何指定 `--last-ignored-msg`

這個參數決定了 AI 閱讀記憶的「起點」，請根據情境選擇正確的訊息內容：

### 1. 啟動全新任務 (New Task)
*   **作法**：指定目前對話框中**最後一則**人類的訊息或系統訊息。
*   **效果**：AI 會將此訊息視為「過去的歷史」，並在「下一則」新訊息出現時才開始反應。這能確保 AI 帶著身分揭露優雅地進入對話。

### 2. 中斷後恢復任務 (Resuming / Re-takeover)
*   **作法**：指定與上次啟動時**完全相同**的訊息。
*   **效果**：這能保持「任務視窗」的一致性。AI 會讀取該訊息之後的所有日誌與對話紀錄（包含它自己之前說過的話），確保它不會忘記已經談妥的事實（如預約時間、停車位等）。

### 3. 修正重複回覆/迴圈 (Loop Correction)
*   **作法**：指定**最新的一則**訊息（甚至是 AI 剛發錯的那則）作為忽略點。
*   **效果**：這會強制 AI 「忘記」之前的衝突點，重新開始監控。

## 使用範例
```bash
python3 run.py --chat "對象名稱" --last-ignored-msg "最後一則要忽略的訊息內容" --task "任務詳細描述..."
```

## 維護與驗證
變更邏輯後，請務必執行單元測試確保接管行為正確：
```bash
python3 run_line_tests.py
```
