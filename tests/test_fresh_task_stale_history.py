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
        return str(getattr(response, 'text', '')).strip()

@pytest.mark.asyncio
async def test_ai_trap_at_thank_you():
    """
    TRAP TEST: History ends at "沒了 謝謝" (User input).
    Verify AI starts new task instead of just saying "You're welcome" and ending.
    """
    task = """啟動一個跟店員的訂位流程。需求如下：
預約 5/11 13:00 (若滿則順延一小時或改 5/12) 
2大1小，需靠窗沙發、插座、推車空間與兒童椅具，
註記慶生、全員忌海鮮堅果且一員全素，
並請保留停車位，若無車位則提供鄰近資訊，並確認有無哺乳室。"""

    history = [
        {"text": "關於外送相關規定，我正為您查閱門禁與包裹管理辦法，請稍候。", "is_self_dom": True, "has_hermes_prefix": True, "timestamp": "8:36 PM"},
        {"text": "根據《門禁管制辦法》，外送員需換證並經保全通報後才可上樓。還有其他想了解的嗎？", "is_self_dom": True, "has_hermes_prefix": True, "timestamp": "8:38 PM"},
        {"text": "沒了 謝謝", "is_self_dom": False, "has_hermes_prefix": False, "timestamp": "8:45 PM"}
    ]
    
    out = await run_ai_test(task, history)
    
    print(f"\n[TRAP TEST] AI Response: {out}")
    
    # CRITICAL ASSERTION: Should NOT end just because the last message was "thanks"
    assert "[CONVERSATION_ENDED" not in out, "TRAP SPRUNG: AI ended the task because it saw 'thanks' in old history."
    assert "5/11" in out or "訂位" in out, "AI failed to address the new task."
