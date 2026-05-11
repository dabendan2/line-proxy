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
    # Tags that SHOULD be stripped
    tags = ["msg[WAIT_FOR_USER_INPUT]", "msg[AGENT_INPUT_NEEDED, reason=\"a\"]"]
    
    for t in tags:
        with patch("google.genai.Client") as m_cli, \
             patch("line_utils.send_message", new_callable=AsyncMock) as m_send, \
             patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=[]):
            m_cli.return_value.models.generate_content.return_value = MockResponse(t)
            p = LineProxyEngine(mock_page, "t", "t", api_key="f")
            await p.generate_and_send_reply([{"text": "m", "is_self_dom": False}])
            
            # Check the message sent to the user (excluding system prefixes if any)
            sent_text = m_send.call_args[0][1]
            # Ensure the specific AI tag brackets are gone
            assert "[WAIT_FOR_USER_INPUT]" not in sent_text
            assert "[AGENT_INPUT_NEEDED" not in sent_text
            assert "msg" in sent_text

@pytest.mark.asyncio
async def test_tool_access_tag_stripping(mock_page):
    # TOOL_ACCESS_NEEDED is special because it triggers an additional "正在執行" message
    t = "msg[TOOL_ACCESS_NEEDED, tool=\"t\", query=\"q\"]"
    with patch("google.genai.Client") as m_cli, \
         patch("line_utils.send_message", new_callable=AsyncMock) as m_send, \
         patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=[]), \
         patch("httpx.AsyncClient") as m_http:
        
        m_cli.return_value.models.generate_content.return_value = MockResponse(t)
        # Mock successful tool call to avoid error brackets
        m_http.return_value.__aenter__.return_value.post.return_value = MagicMock(
            json=lambda: {"choices": [{"message": {"content": "res"}}]},
            status_code=200,
            raise_for_status=lambda: None
        )
        
        p = LineProxyEngine(mock_page, "t", "t", api_key="f")
        # We need to mock the second call to generate_content (after tool result)
        m_cli.return_value.models.generate_content.side_effect = [MockResponse(t), MockResponse("final")]
        
        await p.generate_and_send_reply([{"text": "m", "is_self_dom": False}])
        
        # Verify the message with the tag was stripped
        all_sent = [call[0][1] for call in m_send.call_args_list]
        assert any("msg" in s and "[TOOL_ACCESS_NEEDED" not in s for s in all_sent)

@pytest.mark.asyncio
async def test_tool_error_reporting(mock_page):
    with patch("google.genai.Client") as m_cli, \
         patch("line_utils.send_message", new_callable=AsyncMock) as m_send, \
         patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=[]), \
         patch("httpx.AsyncClient") as m_http:
        m_cli.return_value.models.generate_content.return_value = MockResponse('[TOOL_ACCESS_NEEDED, tool="web", query="q"]')
        m_http.return_value.__aenter__.return_value.post.side_effect = Exception("Offline")
        p = LineProxyEngine(mock_page, "t", "t", api_key="f")
        await p.generate_and_send_reply([{"text": "m", "is_self_dom": False}])
        assert any("執行失敗: Offline" in str(c) for c in m_send.call_args_list)
