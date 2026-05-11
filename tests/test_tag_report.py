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

async def run_ai_test(task, history):
    mock_page = MagicMock()
    mock_page.bring_to_front = AsyncMock()
    with patch("line_utils.send_message", new_callable=AsyncMock) as mock_send, \
         patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=[]), \
         patch("line_utils.select_chat", new_callable=AsyncMock, return_value={"status": "success"}):
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task=task, api_key=api_key)
        
        # Capture raw response
        response = proxy.client.models.generate_content(
            model=proxy.model_name, 
            contents=proxy._build_prompt(proxy.history.get_full_context(history, []))
        )
        return str(getattr(response, 'text', '')).strip(), proxy

@pytest.mark.asyncio
async def test_structured_report_in_tag():
    """
    Verify the AI embeds a structured summary INSIDE the [IMPLICIT_ENDED] tag.
    This allows the engine and unit tests to capture facts directly from the tag.
    """
    task = "訂位並確認哺乳室"
    history = [
        {"text": "5/12 13:00 有位子嗎？", "is_self_dom": True},
        {"text": "有的，已幫您保留位子。", "is_self_dom": False},
        {"text": "那店內有哺乳室嗎？", "is_self_dom": True},
        {"text": "沒有，只能用廁所。", "is_self_dom": False},
        {"text": "好的，謝謝您的協助，辛苦了！", "is_self_dom": True},
        {"text": "好的", "is_self_dom": False}
    ]
    
    raw_response, proxy = await run_ai_test(task, history)
    parsed = proxy._parse_response(raw_response)
    
    print(f"\n[TAG PARSE TEST] Raw Response: {raw_response}")
    print(f"[TAG PARSE TEST] Parsed Summary: {parsed['summary']}")
    
    # Assertions on the machine-readable part
    assert "[CONVERSATION_ENDED" in raw_response, f"Exit tag missing. Got: {raw_response}"
    assert "summary=" in raw_response
    
    # Fact Verification
    summary = parsed["summary"]
    assert "5/12" in summary
    assert "13:00" in summary or "1:00" in summary
    assert "廁所" in summary or "無哺乳室" in summary or "沒有哺乳室" in summary
