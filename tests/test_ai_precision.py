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
async def test_ai_precision_question():
    """
    Verify the AI provides PRECISE time info in its question to avoid ambiguity.
    Refusal criteria: "當天還有位子嗎" (Too vague)
    Success criteria: "5/11 13:00 還有位子嗎" (Precise)
    """
    task = """啟動一個跟店員的訂位流程。需求如下：
預約 5/11 13:00 (若滿則順延一小時或改 5/12) 
2大1小，需靠窗沙發、插座、推車空間與兒童椅具。"""

    # Fresh start, no history
    history = []
    
    out = await run_ai_test(task, history)
    
    print(f"\n[PRECISION TEST] AI Response: {out}")
    
    # Negative test: should not be vague
    assert "當天還有位子嗎" not in out, "Question is too vague. AI should specify the time."
    
    # Positive test: should specify time
    assert "13:00" in out or "1:00" in out, "AI failed to specify the precise time (13:00) in its question."
    assert "5/11" in out, "AI failed to specify the precise date (5/11) in its question."
