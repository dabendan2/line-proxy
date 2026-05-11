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

def get_mock_response(text):
    return MockResponse(text)

@pytest.mark.asyncio
async def test_incremental_disclosure_enforcement(mock_page):
    complex_task = "預訂5/11 13:00 2大2小 要求1個兒童餐具 及保留停車位。"
    with patch("google.genai.Client") as mock_client_class,          patch("line_utils.send_message", new_callable=AsyncMock) as mock_send:
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = get_mock_response(
            "您好，我是 俊羽 的 AI 代理。想預訂 5/11 13:00 還有位置嗎？ [WAIT_FOR_USER_INPUT]"
        )
        proxy = LineProxyEngine(page=mock_page, chat_name="娜比", task=complex_task, api_key="fake")
        await proxy.generate_and_send_reply([])
        mock_send.assert_called_once()

@pytest.mark.asyncio
async def test_pivot_protection_triggered(mock_page):
    task = "預訂 5/11 13:00"
    history = [{"text": "13:00 沒位置了，15:00 可以嗎？", "is_self_dom": False}]
    with patch("google.genai.Client") as mock_client_class,          patch("line_utils.send_message", new_callable=AsyncMock):
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = get_mock_response(
            '[AGENT_INPUT_NEEDED, reason="時段不符，需確認替代時段"]'
        )
        proxy = LineProxyEngine(page=mock_page, chat_name="娜比", task=task, api_key="fake")
        await proxy.generate_and_send_reply(history)
        assert "AGENT_INPUT_NEEDED: 時段不符" in proxy.state["final_report"]

@pytest.mark.asyncio
async def test_all_end_tags_exit_loop(mock_page):
    tags = [
        ('[AGENT_INPUT_NEEDED, reason="test"]', 120),
        ('[IMPLICIT_ENDED, reason="test"]', 300),
        ('[EXPLICIT_ENDED]', 120)
    ]
    for tag_text, expected_wait in tags:
        with patch("google.genai.Client") as mock_client_class,              patch("line_utils.send_message", new_callable=AsyncMock):
            mock_client = mock_client_class.return_value
            mock_client.models.generate_content.return_value = get_mock_response(tag_text)
            proxy = LineProxyEngine(page=mock_page, chat_name="test", task="task", api_key="fake")
            now = time.time()
            await proxy.generate_and_send_reply([{"text": "msg", "is_self_dom": False}])
            assert proxy.state["exit_at"] is not None
