import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import time
import asyncio

# Add src to path
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
async def test_tag_agent_input_needed(mock_page):
    with patch("google.genai.Client") as mock_client_class, \
         patch("line_utils.send_message", new_callable=AsyncMock) as mock_send:
        
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = MockResponse('需要電話。[AGENT_INPUT_NEEDED, reason="缺少聯絡電話"]')
        
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
        now = time.time()
        await proxy.generate_and_send_reply([{"text": "好的", "is_self_dom": False}])
        
        assert proxy.state["exit_at"] is not None
        assert 110 < (proxy.state["exit_at"] - now) < 130
        assert "AGENT_INPUT_NEEDED: 缺少聯絡電話" in proxy.state["final_report"]
        mock_send.assert_called_once_with(mock_page, "需要電話。")

@pytest.mark.asyncio
async def test_tag_implicit_ended(mock_page):
    with patch("google.genai.Client") as mock_client_class, \
         patch("line_utils.send_message", new_callable=AsyncMock) as mock_send:
        
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = MockResponse('好的，那先這樣。[IMPLICIT_ENDED, reason="任務達成"]')
        
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
        now = time.time()
        await proxy.generate_and_send_reply([{"text": "感謝", "is_self_dom": False}])
        
        assert proxy.state["exit_at"] is not None
        assert 290 < (proxy.state["exit_at"] - now) < 310
        assert "IMPLICIT_ENDED: 任務達成" in proxy.state["final_report"]
        mock_send.assert_called_once_with(mock_page, "好的，那先這樣。")

@pytest.mark.asyncio
async def test_tag_explicit_ended(mock_page):
    with patch("google.genai.Client") as mock_client_class, \
         patch("line_utils.send_message", new_callable=AsyncMock) as mock_send:
        
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = MockResponse('再見！[EXPLICIT_ENDED]')
        
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
        now = time.time()
        await proxy.generate_and_send_reply([{"text": "再見", "is_self_dom": False}])
        
        assert proxy.state["exit_at"] is not None
        assert 110 < (proxy.state["exit_at"] - now) < 130
        assert "Conversation explicitly ended" in proxy.state["final_report"]
        mock_send.assert_called_once_with(mock_page, "再見！")

@pytest.mark.asyncio
async def test_loop_exits_on_timeout(mock_page):
    with patch("line_utils.extract_messages", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = [{"text": "哈囉", "is_self_dom": False}]
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
        proxy.state["exit_at"] = time.time() - 10 
        
        with patch.object(proxy.history, 'rebuild_state', return_value={"exit_at": time.time() - 10, "startup_action_needed": False}), \
             patch('asyncio.sleep', return_value=None), \
             patch('line_utils.select_chat', new_callable=AsyncMock, return_value={"status": "success"}), \
             patch.object(proxy, 'generate_and_send_reply', new_callable=AsyncMock):
            await asyncio.wait_for(proxy.run(), timeout=5)
        
        assert True
