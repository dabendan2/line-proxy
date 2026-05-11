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
async def test_script_strips_all_tags(mock_page):
    tags_to_test = [
        "訊息[WAIT_FOR_USER_INPUT]",
        "訊息[AGENT_INPUT_NEEDED, reason=\"test\"]",
        "訊息[IMPLICIT_ENDED, reason=\"test\"]",
        "訊息[EXPLICIT_ENDED]"
    ]
    for raw_text in tags_to_test:
        with patch("google.genai.Client") as mock_client_class,              patch("line_utils.send_message", new_callable=AsyncMock) as mock_send:
            mock_client = mock_client_class.return_value
            mock_client.models.generate_content.return_value = MockResponse(raw_text)
            proxy = LineProxyEngine(page=mock_page, chat_name="test", task="task", api_key="fake")
            await proxy.generate_and_send_reply([{"text": "msg", "is_self_dom": False}])
            # Verify tag is GONE from sent message
            sent_text = mock_send.call_args[0][1]
            assert "[" not in sent_text
            assert "訊息" in sent_text

@pytest.mark.asyncio
async def test_script_action_on_explicit_ended(mock_page):
    with patch("google.genai.Client") as mock_client_class,          patch("line_utils.send_message", new_callable=AsyncMock):
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = MockResponse("再見[EXPLICIT_ENDED]")
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="task", api_key="fake")
        await proxy.generate_and_send_reply([{"text": "msg", "is_self_dom": False}])
        # Verify script-side state change
        assert proxy.state["exit_at"] is not None
        assert "Conversation explicitly ended" in proxy.state["final_report"]
