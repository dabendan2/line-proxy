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

@pytest.mark.asyncio
async def test_final_report_generation():
    """
    Verify the AI generates a structured final report summarizing the chat outcome.
    """
    task = "預約訂位，詢問是否有哺乳室。"
    history = [
        {"text": "請問 5/11 13:00 有位子嗎？", "is_self_dom": True},
        {"text": "有的，已經幫您保留位子了。", "is_self_dom": False},
        {"text": "那請問店內有哺乳室嗎？", "is_self_dom": True},
        {"text": "有的，我們在二樓有哺乳室。", "is_self_dom": False},
        {"text": "好的，謝謝！", "is_self_dom": True},
        {"text": "不客氣，再見。", "is_self_dom": False}
    ]
    
    mock_page = MagicMock()
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task=task, api_key=api_key)
    
    report = await proxy.generate_final_report(history)
    
    print(f"\n[FINAL REPORT TEST] AI Report: \n{report}")
    
    # Validation: Report should summarize the success and specific facts
    assert "成功" in report or "完成" in report
    assert "5/11" in report
    assert "二樓" in report or "哺乳室" in report
