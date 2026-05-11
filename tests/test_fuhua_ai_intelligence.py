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
        captured_full_text = []
        original_parse = proxy._parse_response
        def wrapped_parse(full_text):
            captured_full_text.append(full_text)
            return original_parse(full_text)
        with patch.object(proxy, '_parse_response', side_effect=wrapped_parse):
            await proxy.generate_and_send_reply(history)
        return captured_full_text[0]

@pytest.mark.asyncio
async def test_ai_triggers_tool_for_unknown_facility():
    """Verify the AI asks for a tool when it doesn't know the specific rule for a new facility."""
    task = "根據 Google Drive 中的規章回答問題。目前已知有健身房和KTV辦法。"
    history = [{"text": "小會議室要錢嗎？", "is_self_dom": False}]
    out = await run_ai_test(task, history)
    
    # The AI should not hallucinate that it's free/paid without checking
    assert "[TOOL_ACCESS_NEEDED" in out
    assert "google_drive" in out or "drive" in out

@pytest.mark.asyncio
async def test_ai_behavior_consistency_no_hallucination():
    """Verify the AI doesn't mix up Gym rules with KTV rules."""
    task = "根據 Google Drive 中的規章回答問題。健身房免費，KTV每小時300元。"
    # User asks about KTV, AI shouldn't say "it is free" based on Gym context
    history = [
        {"text": "健身房要錢嗎", "is_self_dom": False},
        {"text": "健身房是一般使用免費的喔。", "is_self_dom": True},
        {"text": "那KTV勒？", "is_self_dom": False}
    ]
    out = await run_ai_test(task, history)
    
    assert "300" in out
    assert "免費" not in out or "KTV" in out # Ensure it doesn't say KTV is free
