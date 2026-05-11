import pytest
import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from engine import LineProxyEngine

api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

@pytest.fixture(autouse=True)
def check_api_key():
    if not api_key:
        pytest.fail("CRITICAL: API KEY missing for real AI test")

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
async def test_real_ai_trigger_wait_for_input():
    out = await run_ai_test("詢問對方明天幾位", [{"text": "我想訂位", "is_self_dom": False}])
    assert "[WAIT_FOR_USER_INPUT]" in out

@pytest.mark.asyncio
async def test_real_ai_trigger_agent_input_needed():
    out = await run_ai_test("幫我訂位", [{"text": "好的，哪一天？", "is_self_dom": False}])
    assert "[AGENT_INPUT_NEEDED" in out

    @pytest.mark.asyncio
    async def test_real_ai_trigger_convo_ended():
        out = await run_ai_test("預訂5/12訂位", [{"text": "已經幫您訂好 5/12 的位置了", "is_self_dom": False}])
        assert "[CONVERSATION_ENDED" in out

    @pytest.mark.asyncio
    async def test_real_ai_trigger_convo_ended_farewell():
        out = await run_ai_test("完成訂位後道別", [{"text": "再見", "is_self_dom": False}])
        assert "[CONVERSATION_ENDED" in out
