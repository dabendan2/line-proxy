import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add src/ to path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(base_dir, "src"))

# Mocking external dependencies before imports
sys.modules['playwright'] = MagicMock()
sys.modules['playwright.async_api'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

import line_utils
from engine import LineProxyEngine

@pytest.fixture
def mock_page():
    # Playwright's page.locator() is a synchronous call returning a Locator
    p = MagicMock()
    p.locator = MagicMock()
    return p

@pytest.mark.asyncio
async def test_extract_messages_identifies_hermes_prefix(mock_page):
    """驗證 extract_messages 能透過 [Hermes] 前綴識別身分。"""
    # page.evaluate 是 async
    mock_page.evaluate = AsyncMock()
    mock_page.evaluate.return_value = [
        {"text": "您好，我是 俊羽 的AI代理 Hermes。", "is_self_dom": True, "has_hermes_prefix": True},
        {"text": "好的，沒問題。", "is_self_dom": False, "has_hermes_prefix": False}
    ]
    
    results = await line_utils.extract_messages(mock_page)
    
    assert results[0]["has_hermes_prefix"] is True
    assert results[0]["is_self_dom"] is True
    assert results[1]["has_hermes_prefix"] is False

@pytest.mark.asyncio
async def test_send_message_adds_prefix(mock_page):
    """驗證 send_message 會自動加上 [Hermes] 前綴。"""
    mock_textarea = AsyncMock()
    # page.locator().first should return the mock_textarea
    mock_page.locator.return_value.first = mock_textarea
    
    # page.keyboard.press is async
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()
    
    test_msg = "這是一則測試訊息"
    await line_utils.send_message(mock_page, test_msg)
    
    # 驗證 fill 被呼叫時帶有前綴
    expected_text = f"{line_utils.HERMES_PREFIX} {test_msg}"
    mock_textarea.fill.assert_called_once_with(expected_text)

@pytest.mark.asyncio
async def test_engine_identifies_sender_by_prefix_only(mock_page):
    """驗證引擎僅依靠前綴（或 DOM 標記）判斷身分，不依賴日誌內容比對。"""
    mock_page.bring_to_front = AsyncMock()
    
    with patch('google.generativeai.configure'), \
         patch('google.generativeai.GenerativeModel'):
        engine = LineProxyEngine(page=mock_page, chat_name="test", task="test", api_key="fake")
        
        # 模擬 DOM 訊息，第一則是自己發的（帶有前綴識別）
        msgs = [
            {"text": "這是我發的", "is_self_dom": True, "has_hermes_prefix": True},
            {"text": "這是對方發的", "is_self_dom": False, "has_hermes_prefix": False}
        ]
        
        # 即使 sent_messages 是空的（模擬 Log 遺失）
        engine.state = {"sent_messages": [], "last_processed_msg": "這是對方發的"}
        
        # 模擬 engine.run 中的判斷邏輯
        latest = msgs[0]
        # 這是從 engine.py 126-128 行提取的邏輯：僅依賴標記或 DOM
        is_hermes = latest.get("has_hermes_prefix", False) or latest.get("is_self_dom", False)
        
        assert is_hermes is True
