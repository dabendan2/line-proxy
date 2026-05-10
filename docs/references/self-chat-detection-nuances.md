# LINE Extension Self-Chat (Keep) 偵測細節

在 LINE Chrome Extension 的個人對話 (Keep) 或與自己的對話中，身分識別存在以下技術坑洞：

## 1. DOM 標籤失效
- **現象**：通常 LINE 使用 `.mdNM08MsgSelf` 與 `.mdNM08MsgOther` 來區分發言者。
- **坑洞**：在個人對話中，**所有**訊息（無論是你發的還是對方發的）都可能被賦予相同的類別或屬性（例如 `data-direction="reverse"`），導致無法單靠 DOM 判斷誰是 AI 誰是人類。

## 2. 回音現象 (The Echo Effect)
- **現象**：AI 代理人重啟後，讀取到自己剛才發出的訊息，誤以為是「對方的需求」，導致對著自己道歉或重複自我介紹。
- **解決方案**：
    1. **日誌優先 (Log-First)**：維護一個本地日誌檔案，明確記錄 `SENT` (AI) 與 `NEW MSG` (對方)。重啟時先載入日誌重建「己方發言清單」。
    2. **內文去背 (Stripped Text Matching)**：比對內文時須進行 `.strip()`，避免因換行符號差異導致身分識別失敗。

## 3. 視覺驗證
- **建議**：開發時應使用 `screenshot` 搭配 `vision_analyze` 確認當前對話視窗的「側邊欄選中狀態」，確保代理人是在正確的目標對話中操作，而非停留在搜尋結果頁面。
