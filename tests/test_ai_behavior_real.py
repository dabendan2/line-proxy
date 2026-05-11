import pytest
import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from engine import LineProxyEngine

# NO SILENT SKIP. If you want to test AI, you must provide the key.
api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

@pytest.fixture(autouse=True)
def check_api_key():
    if not api_key:
        pytest.fail("CRITICAL: GEMINI_API_KEY / GOOGLE_API_KEY is missing. Real AI tests cannot run.")

@pytest.fixture
def mock_page():
    p = MagicMock()
    p.bring_to_front = AsyncMock()
    return p

@pytest.mark.asyncio
async def test_real_ai_noise_robustness(mock_page):
    """
    INTEGRATION TEST: Verifies that the real AI actually filters noise.
    Uses real API to ensure intelligence is as expected.
    """
    messy_history = [
        {"text": "今天天氣真好", "is_self_dom": False, "timestamp": "9:00 AM"},
        {"text": "你看過最新的 Chiikawa 嗎？", "is_self_dom": False, "timestamp": "9:10 AM"},
        {"text": "小八貓好可愛", "is_self_dom": True, "timestamp": "9:15 AM"},
        {"text": "好的，我想預約 5/12 兩位", "is_self_dom": False, "timestamp": "10:00 AM"}
    ]
    
    with patch("line_utils.send_message", new_callable=AsyncMock) as mock_send,          patch("line_utils.select_chat", new_callable=AsyncMock, return_value={"status": "success"}):
        
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="確認 5/12 兩位的訂位", api_key=api_key)
        await proxy.generate_and_send_reply(messy_history)
        
        mock_send.assert_called_once()
        sent_text = str(mock_send.call_args[0][1]).lower()
        
        # Real AI intelligence checks
        assert "預約" in sent_text or "5/12" in sent_text or "位" in sent_text
        assert "chiikawa" not in sent_text, "AI failed to filter Chiikawa noise"
        assert "小八" not in sent_text, "AI failed to filter Hachiware noise"

@pytest.mark.asyncio
async def test_real_ai_tag_generation(mock_page):
    """
    INTEGRATION TEST: Verifies that the real AI actually produces the required tags.
    """
    history = [
        {"text": "我想預約明天兩位", "is_self_dom": False, "timestamp": "10:00 AM"}
    ]
    
    with patch("line_utils.send_message", new_callable=AsyncMock) as mock_send,          patch("line_utils.select_chat", new_callable=AsyncMock, return_value={"status": "success"}):
        
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="詢問對方聯絡電話", api_key=api_key)
        
        captured_full_text = []
        original_parse = proxy._parse_response
        def wrapped_parse(full_text):
            captured_full_text.append(full_text)
            return original_parse(full_text)
        
        with patch.object(proxy, '_parse_response', side_effect=wrapped_parse):
            await proxy.generate_and_send_reply(history)
            
        full_output = captured_full_text[0]
        # Verify AI actually followed instructions to use a tag
        assert any(tag in full_output for tag in ["[WAIT_FOR_USER_INPUT]", "[AGENT_INPUT_NEEDED", "[IMPLICIT_ENDED", "[EXPLICIT_ENDED]"]),             f"AI output missing mandatory state tags: {full_output}"
