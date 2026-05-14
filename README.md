# Chat Agent System

基於 LINE Chrome Extension 的強健 AI 代理人系統，支援多通路擴充、上下文保留與智慧接管。

## 核心特性
- **模組化通路 (Modular Channels)**：支援 LINE、Messenger 等多種通訊平台，底層 AI 邏輯完全解耦。
- **智慧接管 (Smart Takeover)**：啟動時自動判斷對話末端是否需要回覆，避免產生多餘的打招呼或重複自我介紹。
- **身分識別 (Identity Awareness)**：優先解析本地日誌，在發言標籤混亂的環境下，也能精確區分「自己」與「對方」。
- **日誌即狀態 (Log-as-State)**：系統記憶、進度與計時器皆從日誌中即時恢復，無需依賴脆弱的狀態檔。

## 專案結構
```
.
├── src/                # 原始碼 (Python)
│   ├── core/           # 核心決策引擎 (ChatEngine)
│   ├── channels/       # 通路驅動程式 (LINE, etc.)
│   ├── utils/          # 共用工具 (Browser, Locker, Config)
│   └── mcp_server.py   # 通用 MCP 進入點
├── tests/              # 測試套件
├── package.json        # 專案組態 (npm)
├── requirements.txt    # Python 依賴
├── run_line_tests.py   # 測試執行腳本
└── .husky/             # Git Hooks
```

## 參數指南：--last-ignored-msg
此參數定義了 AI 的記憶邊界，請根據情境選擇：
- **新任務**：指定目前對話中**最後一則**人類或系統訊息。AI 會將此視為歷史，從下一則新訊息開始反應。
- **恢復任務**：指定與上次啟動時**完全相同**的訊息。這能確保 AI 讀取之後的所有日誌，不會忘記已談妥的事實。
- **修正迴圈**：指定**最新的一則**（包含 AI 發錯的）訊息。這會強制 AI 忘記衝突點，重新監控。

## 開發與測試
本專案整合了 Husky，所有 Commit 必須通過測試。執行測試時需指定超時限制：
```bash
export TIMEOUT_SET=180 && npm test
```
