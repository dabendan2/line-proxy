# LINE 擴充功能：DOM 時間軸與反轉 (DOM Chronology)

在自動化 LINE Chrome 擴充功能時，發現其 DOM 結構中的訊息排序具有特定反直覺特性。

## 1. 訊息排序特性 (Newest First)
- **觀測結果**：使用 `querySelectorAll` 抓取訊息氣泡時，取得的陣列順序通常是 **「最新訊息在前」**。
- **風險**：若直接將此列表餵給 LLM 作為對話歷史，模型會將「未來的回覆」誤認為「過去的背景」，導致邏輯判斷顛倒（例如：忽略了剛剛才發生的拒絕訊息）。

## 2. 修正方案 (Chronological Reversing)
在 `extract_messages` 邏輯中，必須包含顯式的反轉動作：
```javascript
// JavaScript snippet inside evaluate
const items = Array.from(document.querySelectorAll('.message-bubble'));
const results = items.map(el => ({ text: el.innerText }));
return results.reverse(); // 強制轉換為「舊 -> 新」
```

## 3. 氣泡容器限制
訊息抓取應限制在 **「當前活動聊天室」** 容器內 (`chatroom-module__chatroom`)，以防止在搜尋或切換視窗瞬間抓取到側邊欄的預覽文字。
