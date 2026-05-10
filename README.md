# LINE Proxy Engine

基於 LINE Chrome Extension 的 AI 代理人系統，支援上下文保留與智慧接管。

## 專案結構
```
.
├── src/                # 原始碼 (Python)
│   ├── engine.py       # 核心決策引擎
│   ├── history_manager.py # 日誌與狀態管理
│   ├── line_utils.py   # LINE DOM 操作
│   ├── run.py          # 程式進入點
│   └── etiquette.md    # 社交禮儀規範
├── tests/              # 測試套件
├── package.json        # 專案組態 (npm)
├── requirements.txt    # Python 依賴
├── run_line_tests.py   # 測試執行腳本
└── .husky/             # Git Hooks
```

## 安裝依賴
```bash
pip install -r requirements.txt
npm install
```

## 使用方法
```bash
python3 src/run.py --chat "對象" --last-ignored-msg "..." --task "..."
```

## 開發與測試
本專案整合了 Husky，在每次 commit 前會自動執行單元測試。

手動執行測試：
```bash
npm test
# 或
python3 run_line_tests.py
```

## 參數指南：--last-ignored-msg
此參數定義了 AI 的記憶邊界。
- **新任務**：指定最後一則人類訊息。
- **恢復任務**：指定與上次相同的訊息。
- **修正迴圈**：指定最新一則（包含 AI 發錯的）訊息。
