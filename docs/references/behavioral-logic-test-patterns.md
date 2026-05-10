# Behavioral Logic Test Patterns

這份參考文件詳述了在開發 LINE 代理人時，如何透過單元測試驗證模型的「行為一致性」與「邏輯安全性」，特別是處理非同步 (Async) 環境下的 Mock 坑洞。

## 1. 非同步 Mock 與 `iscoroutinefunction`
在 `engine.py` 中，如果為了相容性同時支援真實 Playwright 呼叫與 Mock 呼叫，通常會使用 `asyncio.iscoroutinefunction` 來判斷是否需要 `await`。

### 坑洞：MagicMock 不是 Coroutine
當使用 `unittest.mock.MagicMock` 取代 `line_utils.send_message` 時，`iscoroutinefunction` 會回傳 `False`。
*   **解決方案**：在測試中明確使用 `AsyncMock`，且在引擎代碼中確保對 `text` 等屬性的存取是安全的。

```python
# 測試中的正確 Mock 方式
mock_send = AsyncMock()
with patch('engine.send_message', mock_send):
    await proxy.generate_and_send_reply(msgs)
    mock_send.assert_called_once()
```

## 2. 驗證「默契靜默」場景
這是使用者最在意的行為：當任務已達成且對方說「好的」時，代理人應保持靜默。

### 測試邏輯：
1.  模擬對話歷史：Hermes 已提供資訊 -> User 回覆「了解」。
2.  模擬模型輸出：模型回覆僅包含 `[END]` 標籤，不含社交文字。
3.  驗證：`mock_send.assert_not_called()`。

## 3. 驗證「聚焦回答」場景
防止代理人像錄音機一樣重複整段預約資訊。

### 測試邏輯：
1.  模擬歷史：已提過「三大兩小」。
2.  模擬提問：店員問「有幾位兒童？」。
3.  模擬回覆：模型輸出「總共 2 位」。
4.  驗證：`assert "5/11" not in sent_text`（確保沒重複日期）。

## 4. 防止「MagicMock」字串流出
在測試環境中，若模型回覆對象 Mock 不完全，`response.text` 可能會回傳 `"<MagicMock ...>"` 字串並真的發送出去。

### 防禦性編碼：
```python
full_text = str(getattr(response, 'text', '')).strip()
if reply_text and "MagicMock" not in reply_text:
    await send_message(page, reply_text)
```
