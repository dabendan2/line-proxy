import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from core.engine import ChatEngine

@pytest.mark.asyncio
@patch('google.genai.Client')
async def test_ai_proposes_terminal_for_zip_file(mock_genai_class):
    """
    Verify that when the prompt contains a zip file, the AI logic processes it.
    We mock the AI response to return a terminal tool request.
    """
    mock_client = mock_genai_class.return_value
    mock_channel = AsyncMock()

    engine = ChatEngine(
        channel=mock_channel,
        chat_name="Test",
        task="解壓縮 code.zip",
        api_key="fake_key"
    )

    # Mock AI response to trigger terminal
    mock_ai_resp = MagicMock()
    mock_ai_resp.text = '[TOOL_ACCESS_NEEDED, tool="terminal", query="unzip /path/to/code.zip"]'
    mock_client.models.generate_content.side_effect = [
        mock_ai_resp,
        MagicMock(text='[CONVERSATION_ENDED, summary="done"]')
    ]

    # Mock execute_hermes_tool to avoid real API calls
    engine.execute_hermes_tool = AsyncMock(return_value="unzipped successfully")

    msgs = [
        {
            "sender": "User",
            "text": "給你代碼",
            "media": {
                "type": "file",
                "name": "code.zip",
                "local_path": "/home/ubuntu/chat-agent/file-cache/test/code.zip"
            }
        }
    ]

    await engine.generate_and_send_reply(msgs)
    
    # Verify the internal state reflects tool usage
    # Technical messages are now recorded in sent_messages but not sent via channel.send_message
    assert any("[系統通知] 工具執行成功" in str(msg) for msg in engine.state["sent_messages"])
