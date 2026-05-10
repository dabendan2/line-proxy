# 穩健對話選擇模式 (Robust Chat Selection Pattern)

為了防止在 LINE 擴充功能中因座標點擊 (`xdotool` 或固定像素) 造成的誤導與失敗，必須採用基於標籤與驗證的選擇模式。

## 1. 核心邏輯 (Selection Logic)
對話選擇不應僅依賴「點擊」，而應包含「點擊 + 驗證」：
1. **檢查現狀**：比對當前聊天室標題 (`chatroomHeader-module__name`)。若已匹配，則無需點擊。
2. **精準定位**：在側邊欄搜尋包含目標名稱的 `chatlist_item`。
3. **執行點擊**：使用 Playwright 的 `locator.click()`。
4. **狀態驗證**：等待標題更新為目標名稱。若超時或不匹配，則判定為選擇失敗。

## 2. 代碼實作 (`line_utils.py`)
```python
async def select_chat(page, chat_name):
    # 1. 驗證標題
    header = page.locator('[class*="chatroomHeader-module__name"]', has_text=chat_name).first
    if await header.is_visible(): return True

    # 2. 定位並點擊側邊欄
    chat_item = page.locator('[class*="chatlistItem-module__chatlist_item"]', has_text=chat_name).first
    if await chat_item.is_visible():
        await chat_item.click()
        # 3. 等待驗證
        try:
            await header.wait_for(state="visible", timeout=5000)
            return True
        except:
            return await header.is_visible()
    return False
```

## 3. 測試準則 (Testing Strategy)
所有對話選擇邏輯必須通過 `tests/test_chat_selection.py` 的驗證，涵蓋：
- **Already Selected**: 避免重複點擊。
- **Successful Navigation**: 驗證點擊與標題變更。
- **Failure Handling**: 處理找不到對話的情況。
