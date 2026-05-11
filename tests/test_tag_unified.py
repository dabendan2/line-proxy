import pytest
import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from engine import LineProxyEngine

api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

@pytest.fixture(autouse=True)
def check_api_key():
    if not api_key:
        pytest.fail("CRITICAL: API KEY missing for AI intelligence test")

async def get_ai_parsed_response(task, history):
    mock_page = MagicMock()
    mock_page.bring_to_front = AsyncMock()
    with patch("line_utils.send_message", new_callable=AsyncMock), \
         patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=[]), \
         patch("line_utils.select_chat", new_callable=AsyncMock, return_value={"status": "success"}):
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task=task, api_key=api_key)
        context = proxy.history.get_full_context(history, [])
        prompt = proxy._build_prompt(context)
        response = proxy.client.models.generate_content(model=proxy.model_name, contents=prompt)
        raw_text = str(getattr(response, 'text', '')).strip()
        parsed = proxy._parse_response(raw_text)
        return raw_text, parsed

@pytest.mark.asyncio
async def test_unified_conversation_ended_tag():
    """
    Verify the AI uses the new unified [CONVERSATION_ENDED] tag.
    """
    task = "簡單訂位"
    history = [
        {"text": "5/12 13:00 有位子嗎？", "is_self_dom": True},
        {"text": "有的，已保留。", "is_self_dom": False},
        {"text": "好的，謝謝！", "is_self_dom": True},
        {"text": "好的", "is_self_dom": False}
    ]
    
    raw_text, parsed = await get_ai_parsed_response(task, history)
    
    print(f"\n[TAG UNIFIED TEST] Raw Response: {raw_text}")
    
    # Assert tag exists and attributes are present
    assert "[CONVERSATION_ENDED" in raw_text
    assert "summary=" in raw_text
    assert parsed["conversation_ended"] is True
    assert parsed["summary"] is not None
