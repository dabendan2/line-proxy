---
name: line-proxy
description: 基於 LINE Chrome Extension 的強健 AI 代理人系統，支援全上下文模式與智慧狀態標籤。
tags: [line, proxy, automation]
---

# LINE 代理人引擎 (LINE Proxy Engine)

這是一套強健的 AI 驅動代理系統，旨在代表使用者處理 LINE 對話。具備精準的身分偵測、持久化狀態管理與自動化測試機制。

## 核心特性
- **全上下文模式 (Full Context Mode)**：廢除舊有的訊息邊界錨點，模型會讀取完整的對話歷史，從而提高決策的連貫性並避免重複。
- **智慧接管 (Smart Takeover)**：啟動時自動判斷對話末端是否需要回覆，避免產生多餘的社交動作。
- **身分識別 (Identity Awareness)**：能精確區分「自己」與「對方」，並自動處理 `[Hermes]` 前綴。
- **狀態標籤系統 (Status Tag System)**：
    *   `[WAIT_FOR_USER_INPUT]`：靜默等待回覆。
    *   `[AGENT_INPUT_NEEDED]`：需人工介入（守候 2 分鐘）。
    *   `[IMPLICIT_ENDED]`：任務達成（守候 5 分鐘）。
    *   `[EXPLICIT_ENDED]`：正式道別（守候 2 分鐘）。
- **PID 鎖定 (PID Locking)**：防止同一個對話窗口有多個代理人實例同時運行。

## 檔案結構
- `run.py`: CLI 執行入口（固定使用 CDP Port 9222）。
- `engine.py`: 核心決策邏輯與標籤處理。
- `line_utils.py`: LINE DOM 操作工具（Playwright）。
- `history_manager.py`: 管理對話日誌與狀態恢復。
- `etiquette.md`: 社交禮儀與互動規範。
- `tests/`: 包含循序漸進、雜訊抗性與標籤邏輯的單元測試。

## 使用範例
```bash
# 啟動任務
python3 run.py --chat "對象名稱" --task "任務詳細描述..."
```

## 維護與驗證
變更邏輯後，請務必執行單元測試確保系統穩定：
```bash
python3 run_line_tests.py
```
或直接使用 pytest：
```bash
pytest tests/
```
