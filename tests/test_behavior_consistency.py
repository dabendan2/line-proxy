import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# Define shared mocks
mock_extract = AsyncMock()
mock_send = AsyncMock()
mock_genai_client_inst = MagicMock()
mock_genai_client_class = MagicMock(return_value=mock_genai_client_inst)

with patch.dict('sys.modules', {
    'playwright': MagicMock(),
    'playwright.async_api': MagicMock(),
    'google.genai': MagicMock(Client=mock_genai_client_class),
    'line_utils': MagicMock(
        extract_messages=mock_extract,
        send_message=mock_send,
        HERMES_PREFIX="[Hermes]"
    )
}):
    from engine import LineProxyEngine
    from history_manager import HistoryManager

@pytest.fixture(autouse=True)
def reset_mocks():
    mock_extract.reset_mock()
    mock_send.reset_mock()
    mock_genai_client_inst.models.generate_content.reset_mock()

@pytest.fixture
def mock_page():
    p = MagicMock()
    p.bring_to_front = AsyncMock()
    return p

class MockResponse:
    def __init__(self, text):
        self.text = text

@pytest.mark.asyncio
async def test_reason_consulting_mapping(mock_page):
    mock_genai_client_inst.models.generate_content.return_value = MockResponse('問問俊羽。[AGENT_INPUT_NEEDED, reason="詢問電話"]')
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    now = time.time()
    await proxy.generate_and_send_reply([{"text": "電話？", "is_self_dom": False, "timestamp": "10:00 AM"}])
    
    assert proxy.state["exit_at"] is not None
    assert 110 < (proxy.state["exit_at"] - now) < 130
    assert proxy.state["final_report"] == "AGENT_INPUT_NEEDED: 詢問電話"

@pytest.mark.asyncio
async def test_no_redundant_intro_logic(mock_page):
    msgs = [
        {"text": "哈囉", "is_self_dom": False, "timestamp": "10:00 AM"}, 
        {"text": "我是 Hermes", "is_self_dom": True, "timestamp": "10:01 AM"}
    ]
    
    mock_genai_client_inst.models.generate_content.return_value = MockResponse("這部分沒問題。")
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    proxy.state["sent_messages"] = ["我是 Hermes"]
    
    await proxy.generate_and_send_reply(msgs)
    
    mock_send.assert_called_once()
    sent_text = str(mock_send.call_args[0][1])
    # Should not contain "Hermes" if intro already done
    assert "Hermes" not in sent_text

def test_history_manager_context_includes_timestamps():
    mgr = HistoryManager(chat_name="test")
    msgs = [
        {"text": "早安", "is_self_dom": False, "timestamp": "8:00 AM"},
        {"text": "你好", "is_self_dom": True, "timestamp": "8:05 AM"}
    ]
    context = mgr.get_full_context(msgs, [])
    assert "[8:00 AM] User/Staff: 早安" in context[0]
    assert "[8:05 AM] Hermes (AI Proxy): 你好" in context[1]

def test_rebuild_state_takeover_logic():
    mgr = HistoryManager(chat_name="test")
    msgs = [
        {"text": "有位子嗎", "is_self_dom": True, "timestamp": "1:00 PM"},
        {"text": "有的", "is_self_dom": False, "timestamp": "1:05 PM"}
    ]
    state = mgr.rebuild_state(msgs, "訂位")
    assert state["startup_action_needed"] is True
    assert state["last_processed_msg"] == "___TAKEOVER___"

    msgs2 = [
        {"text": "有的", "is_self_dom": False, "timestamp": "1:05 PM"},
        {"text": "好的謝謝", "is_self_dom": True, "timestamp": "1:10 PM"}
    ]
    state2 = mgr.rebuild_state(msgs2, "訂位")
    assert state2["startup_action_needed"] is False
    assert state2["last_processed_msg"] == "好的謝謝"
