import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import time
import asyncio

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from engine import LineProxyEngine

class MockResponse:
    def __init__(self, text):
        self.text = text

@pytest.fixture
def mock_page():
    p = MagicMock()
    p.bring_to_front = AsyncMock()
    return p

@pytest.mark.asyncio
async def test_reason_consulting_mapping(mock_page):
    with patch("google.genai.Client") as mock_client_class, \
         patch("line_utils.send_message", new_callable=AsyncMock), \
         patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=[]):
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = MockResponse('問問俊羽。[AGENT_INPUT_NEEDED, reason="詢問電話"]')
        
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
    
    with patch("google.genai.Client") as mock_client_class, \
         patch("line_utils.send_message", new_callable=AsyncMock) as mock_send, \
         patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=[]):
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = MockResponse("這部分沒問題。")
        
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
        proxy.state["sent_messages"] = ["我是 Hermes"]
        
        await proxy.generate_and_send_reply(msgs)
        mock_send.assert_called_once()
        sent_text = str(mock_send.call_args[0][1])
        assert "Hermes" not in sent_text

def test_history_manager_context_includes_timestamps():
    from history_manager import HistoryManager
    mgr = HistoryManager(chat_name="test")
    msgs = [
        {"text": "早安", "is_self_dom": False, "timestamp": "8:00 AM"},
        {"text": "你好", "is_self_dom": True, "timestamp": "8:05 AM"}
    ]
    context = mgr.get_full_context(msgs, [])
    assert "[8:00 AM] User/Staff: 早安" in context[0]
    assert "[8:05 AM] Hermes (AI Proxy): 你好" in context[1]
