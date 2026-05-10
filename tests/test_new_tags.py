import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import time
import asyncio

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
        HERMES_PREFIX="[Hermes]",
        select_chat=AsyncMock(return_value={"status": "success"})
    )
}):
    from engine import LineProxyEngine

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
async def test_tag_agent_input_needed(mock_page):
    mock_genai_client_inst.models.generate_content.return_value = MockResponse('需要電話。[AGENT_INPUT_NEEDED, reason="缺少聯絡電話"]')
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    now = time.time()
    await proxy.generate_and_send_reply([{"text": "好的", "is_self_dom": False}])
    
    assert proxy.state["exit_at"] is not None
    # Wait time should be 120s
    assert 110 < (proxy.state["exit_at"] - now) < 130
    assert "AGENT_INPUT_NEEDED: 缺少聯絡電話" in proxy.state["final_report"]
    # Check if tag is stripped from message
    mock_send.assert_called_once_with(mock_page, "需要電話。")

@pytest.mark.asyncio
async def test_tag_implicit_ended(mock_page):
    mock_genai_client_inst.models.generate_content.return_value = MockResponse('好的，那先這樣。[IMPLICIT_ENDED, reason="任務達成"]')
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    now = time.time()
    await proxy.generate_and_send_reply([{"text": "感謝", "is_self_dom": False}])
    
    assert proxy.state["exit_at"] is not None
    # Wait time should be 300s
    assert 290 < (proxy.state["exit_at"] - now) < 310
    assert "IMPLICIT_ENDED: 任務達成" in proxy.state["final_report"]
    mock_send.assert_called_once_with(mock_page, "好的，那先這樣。")

@pytest.mark.asyncio
async def test_tag_explicit_ended(mock_page):
    mock_genai_client_inst.models.generate_content.return_value = MockResponse('再見！[EXPLICIT_ENDED]')
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    now = time.time()
    await proxy.generate_and_send_reply([{"text": "再見", "is_self_dom": False}])
    
    assert proxy.state["exit_at"] is not None
    # Wait time should be 120s
    assert 110 < (proxy.state["exit_at"] - now) < 130
    assert "Conversation explicitly ended" in proxy.state["final_report"]
    mock_send.assert_called_once_with(mock_page, "再見！")

@pytest.mark.asyncio
async def test_loop_exits_on_timeout(mock_page):
    mock_extract.return_value = [{"text": "哈囉", "is_self_dom": False}]
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    
    # Pre-set state to trigger immediate exit
    proxy.state["exit_at"] = time.time() - 10 
    
    # We need to mock rebuild_state to NOT overwrite our exit_at
    with patch.object(proxy.history, 'rebuild_state', return_value={"exit_at": time.time() - 10, "startup_action_needed": False}):
        with patch('asyncio.sleep', return_value=None): 
            await asyncio.wait_for(proxy.run(), timeout=5)
    
    assert True
