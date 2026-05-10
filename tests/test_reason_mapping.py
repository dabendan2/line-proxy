import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import time

# Ensure src is in path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(base_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Mock line_utils for all tests
mock_line_utils = MagicMock()
mock_line_utils.extract_messages = AsyncMock(return_value=[])
mock_line_utils.send_message = AsyncMock()

with patch.dict('sys.modules', {
    'playwright': MagicMock(),
    'playwright.async_api': MagicMock(),
    'google.genai': MagicMock(),
    'line_utils': mock_line_utils
}):
    from engine import LineProxyEngine

@pytest.fixture
def mock_page():
    p = MagicMock()
    p.bring_to_front = AsyncMock()
    return p

@pytest.fixture
def mock_genai():
    mock_client_inst = MagicMock()
    # Ensure fresh state for each test
    mock_line_utils.extract_messages.reset_mock()
    mock_line_utils.send_message.reset_mock()
    
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="Etiquette")))))), \
         patch('engine.genai.Client', return_value=mock_client_inst):
        yield mock_client_inst

@pytest.mark.asyncio
async def test_reason_consulting_wait_time(mock_page, mock_genai):
    """驗證 reason='consulting' 是否對應 120 秒等待。"""
    mock_resp = MagicMock()
    mock_resp.text = '我問問俊羽。[END, reason="consulting", report="詢問電話"]'
    mock_genai.models.generate_content.return_value = mock_resp
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    now = time.time()
    
    await proxy.generate_and_send_reply([{"text": "電話？", "is_self_dom": False}])
    
    # 預期等待時間約為 120 秒
    assert 115 < (proxy.state["exit_at"] - now) < 125
    assert proxy.state["final_report"] == "詢問電話"

@pytest.mark.asyncio
async def test_reason_accomplished_wait_time(mock_page, mock_genai):
    """驗證 reason='accomplished' 是否對應 300 秒等待。"""
    mock_resp = MagicMock()
    mock_resp.text = '[END, reason="accomplished", report="預約完成"]'
    mock_genai.models.generate_content.return_value = mock_resp
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    now = time.time()
    
    await proxy.generate_and_send_reply([{"text": "好的", "is_self_dom": False}])
    
    # 預期等待時間約為 300 秒 (5分鐘)
    assert 295 < (proxy.state["exit_at"] - now) < 305
    assert proxy.state["final_report"] == "預約完成"

@pytest.mark.asyncio
async def test_reason_goodbye_wait_time(mock_page, mock_genai):
    """驗證 reason='goodbye' 是否對應 120 秒等待。"""
    mock_resp = MagicMock()
    mock_resp.text = '再見！[END, reason="goodbye", report="雙方道別"]'
    mock_genai.models.generate_content.return_value = mock_resp
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    now = time.time()
    
    await proxy.generate_and_send_reply([{"text": "掰掰", "is_self_dom": False}])
    
    # 預期等待時間約為 120 秒
    assert 115 < (proxy.state["exit_at"] - now) < 125
    assert proxy.state["final_report"] == "雙方道別"
