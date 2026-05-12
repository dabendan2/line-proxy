import pytest
import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from dotenv import load_dotenv

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from engine import LineProxyEngine
import line_utils

# Load env explicitly for local pytest runs
load_dotenv(dotenv_path=Path.home() / ".hermes" / ".env")

# Use a very specific name to avoid any pytest fixture collision
TEST_KEY_VALUE = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "MISSING"
OWNER_NAME_VAL = "俊羽"

@pytest.fixture(autouse=True)
def verify_test_env():
    if TEST_KEY_VALUE == "MISSING":
        pytest.fail("CRITICAL: API KEY missing for AI intelligence test")

async def run_ai_test(task, history):
    mock_page = MagicMock()
    mock_page.bring_to_front = AsyncMock()
    with patch("line_utils.send_message", new_callable=AsyncMock) as mock_send, \
         patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=[]), \
         patch("line_utils.select_chat", new_callable=AsyncMock, return_value={"status": "success"}):
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task=task, api_key=TEST_KEY_VALUE)
        captured_full_text = []
        original_parse = proxy._parse_response
        def wrapped_parse(full_text):
            captured_full_text.append(full_text)
            return original_parse(full_text)
        with patch.object(proxy, '_parse_response', side_effect=wrapped_parse):
            await proxy.generate_and_send_reply(history)
        return captured_full_text[0]

@pytest.mark.asyncio
async def test_ai_precision_question():
    task = """1. **階段：確認身份** - 確認聯繫對象是否為「娜比燒肉」。
2. **階段：預約** - 預約 5/11 13:00 2大1小。"""
    history = []
    out = await run_ai_test(task, history)
    assert "娜比" in out or "燒肉" in out

@pytest.mark.asyncio
async def test_strict_title_matching_already_selected():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()
    mock_header = AsyncMock()
    mock_header.is_visible = AsyncMock(return_value=True)
    mock_header.inner_text = AsyncMock(return_value="dabendan.test")
    mock_locator = MagicMock()
    mock_locator.first = mock_header
    mock_page.locator = MagicMock(return_value=mock_locator)
    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "dabendan.test")
        assert result["status"] == "success"

@pytest.mark.asyncio
async def test_select_chat_with_search_success():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()
    mock_header = AsyncMock()
    mock_header.is_visible = AsyncMock(return_value=False)
    mock_title = AsyncMock()
    mock_title.inner_text = AsyncMock(return_value="dabendan.test")
    mock_title.click = AsyncMock()
    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=1)
    mock_list.nth = MagicMock(return_value=mock_title)
    mock_search = AsyncMock()
    mock_search.click = AsyncMock()
    mock_search.fill = AsyncMock()

    def side_effect(selector, **kwargs):
        if "Header" in selector or "header" in selector:
            l = MagicMock(); l.first = mock_header; return l
        if "Search" in selector or "搜尋" in selector:
            l = MagicMock(); l.first = mock_search; return l
        # Default fallback for new selectors
        l = MagicMock()
        l.first = AsyncMock()
        l.first.is_visible = AsyncMock(return_value=False)
        if "title" in selector:
            return mock_list
        return l

    mock_page.locator = MagicMock(side_effect=side_effect)
    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "dabendan.test")
        assert result["status"] == "success"

@pytest.mark.asyncio
async def test_select_chat_not_found():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()
    mock_header = AsyncMock()
    mock_header.is_visible = AsyncMock(return_value=False)
    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=0)
    mock_search = AsyncMock()
    mock_search.click = AsyncMock()
    mock_search.fill = AsyncMock()

    def side_effect(selector, **kwargs):
        if "Header" in selector or "header" in selector:
            l = MagicMock(); l.first = mock_header; return l
        if "Search" in selector or "搜尋" in selector:
            l = MagicMock(); l.first = mock_search; return l
        # Default fallback
        l = MagicMock()
        l.first = AsyncMock()
        l.first.is_visible = AsyncMock(return_value=False)
        if "title" in selector:
            return mock_list
        return l

    mock_page.locator = MagicMock(side_effect=side_effect)
    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "ghost")
        assert result["status"] == "not_found"

@pytest.mark.asyncio
async def test_reason_consulting_mapping():
    mock_page = MagicMock()
    with patch("google.genai.Client") as mock_client_class, \
         patch("line_utils.send_message", new_callable=AsyncMock), \
         patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=[]):
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = MagicMock(text=f'問問{OWNER_NAME_VAL}。[AGENT_INPUT_NEEDED, reason="詢問電話"]')
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="test", api_key=TEST_KEY_VALUE)
        await proxy.generate_and_send_reply([])
        assert "AGENT_INPUT_NEEDED" in proxy.state.get("final_report", "")
        assert "詢問電話" in proxy.state.get("final_report", "")

@pytest.mark.asyncio
async def test_ai_trap_at_thank_you():
    task = "啟動訂位流程：5/11 13:00 2大1小。"
    history = [
        {"text": "外送員需換證。", "is_self_dom": True, "has_hermes_prefix": True},
        {"text": "沒了 謝謝", "is_self_dom": False, "has_hermes_prefix": False}
    ]
    out = await run_ai_test(task, history)
    assert any(kw in out for kw in ["訂位", "預約", "預訂", "訂餐"])

@pytest.mark.asyncio
async def test_real_ai_trigger_wait_for_input():
    out = await run_ai_test("詢問對方明天幾位", [{"text": "我想訂位", "is_self_dom": False}])
    assert "[WAIT_FOR_USER_INPUT]" in out

@pytest.mark.asyncio
async def test_real_ai_trigger_agent_input_needed():
    out = await run_ai_test("幫我訂位", [{"text": "好的，哪一天？", "is_self_dom": False}])
    assert "[AGENT_INPUT_NEEDED" in out
