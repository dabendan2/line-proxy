import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

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
async def test_noise_robustness_unrelated_chatter(mock_page):
    """驗證代理人在混亂歷史中是否仍能聚焦於主任務 (訂位)"""
    messy_history = [
        {"text": "今天天氣真好", "is_self_dom": False, "timestamp": "9:00 AM"},
        {"text": "對啊，聽說明天會下雨", "is_self_dom": True, "timestamp": "9:05 AM"},
        {"text": "你看過最新的 Chiikawa 嗎？", "is_self_dom": False, "timestamp": "9:10 AM"},
        {"text": "小八貓好可愛", "is_self_dom": True, "timestamp": "9:15 AM"},
        {"text": "好的，我想預約 5/12 兩位", "is_self_dom": False, "timestamp": "10:00 AM"}
    ]
    
    with patch("google.genai.Client") as mock_client_class, \
         patch("line_utils.send_message", new_callable=AsyncMock) as mock_send:
        
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = MockResponse(
            "好的，已為您詢問 5/12 兩位的訂位。"
        )
        
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位 5/12 兩位", api_key="fake")
        await proxy.generate_and_send_reply(messy_history)
        
        mock_send.assert_called_once()
        sent_text = str(mock_send.call_args[0][1])
        assert "5/12" in sent_text
        assert "Chiikawa" not in sent_text
        assert "天氣" not in sent_text

@pytest.mark.asyncio
async def test_noise_robustness_conflicting_info(mock_page):
    """驗證代理人面對歷史中的衝突資訊（如舊的錯誤時間）時，是否能聚焦於最新任務"""
    conflict_history = [
        {"text": "我想訂 5/11", "is_self_dom": False, "timestamp": "昨日 10:00 AM"},
        {"text": "[Hermes] 抱歉 5/11 沒位子了", "is_self_dom": True, "timestamp": "昨日 10:05 AM"},
        {"text": "那改 5/12 好了", "is_self_dom": False, "timestamp": "10:00 AM"}
    ]
    
    with patch("google.genai.Client") as mock_client_class, \
         patch("line_utils.send_message", new_callable=AsyncMock) as mock_send:
        
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = MockResponse(
            "請問 5/12 是否有位子？"
        )
        
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位 5/12", api_key="fake")
        await proxy.generate_and_send_reply(conflict_history)
        
        sent_text = str(mock_send.call_args[0][1])
        assert "5/12" in sent_text
        assert "5/11" not in sent_text
