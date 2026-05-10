import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

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
async def test_noise_robustness_unrelated_chatter(mock_page):
    """驗證代理人在混亂歷史中是否仍能聚焦於主任務 (訂位)"""
    # 混亂歷史：包含關於天氣和 Chiikawa 的閒聊
    messy_history = [
        {"text": "今天天氣真好", "is_self_dom": False, "timestamp": "9:00 AM"},
        {"text": "對啊，聽說明天會下雨", "is_self_dom": True, "timestamp": "9:05 AM"},
        {"text": "你看過最新的 Chiikawa 嗎？", "is_self_dom": False, "timestamp": "9:10 AM"},
        {"text": "小八貓好可愛", "is_self_dom": True, "timestamp": "9:15 AM"},
        {"text": "好的，我想預約 5/12 兩位", "is_self_dom": False, "timestamp": "10:00 AM"}
    ]
    
    # 模擬模型輸出：應聚焦於訂位而非閒聊
    mock_genai_client_inst.models.generate_content.return_value = MockResponse(
        "好的，已為您詢問 5/12 兩位的訂位。"
    )
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位 5/12 兩位", api_key="fake")
    await proxy.generate_and_send_reply(messy_history)
    
    # 驗證發出的訊息是否與訂位相關，且沒有提到閒聊內容
    mock_send.assert_called_once()
    sent_text = str(mock_send.call_args[0][1])
    
    assert "5/12" in sent_text
    assert "Chiikawa" not in sent_text
    assert "天氣" not in sent_text

@pytest.mark.asyncio
async def test_noise_robustness_conflicting_info(mock_page):
    """驗證代理人面對歷史中的衝突資訊（如舊的錯誤時間）時，是否能聚焦於最新任務"""
    # 衝突歷史：之前曾說過 5/11，但最新任務是 5/12
    conflict_history = [
        {"text": "我想訂 5/11", "is_self_dom": False, "timestamp": "昨日 10:00 AM"},
        {"text": "[Hermes] 抱歉 5/11 沒位子了", "is_self_dom": True, "timestamp": "昨日 10:05 AM"},
        {"text": "那改 5/12 好了", "is_self_dom": False, "timestamp": "10:00 AM"}
    ]
    
    mock_genai_client_inst.models.generate_content.return_value = MockResponse(
        "請問 5/12 是否有位子？"
    )
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位 5/12", api_key="fake")
    await proxy.generate_and_send_reply(conflict_history)
    
    sent_text = str(mock_send.call_args[0][1])
    assert "5/12" in sent_text
    assert "5/11" not in sent_text
