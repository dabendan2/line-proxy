import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from core.engine import ChatEngine
from channels.base import BaseChannel

@pytest.mark.asyncio
async def test_image_gen_tag_and_notification():
    """驗證當解析到 image_gen 標籤時，會調用本地邏輯"""
    mock_channel = AsyncMock(spec=BaseChannel)
    mock_channel.extract_messages.return_value = [
        {"sender": "User", "text": "幫我畫一張橘貓"}
    ]

    with patch("core.engine.HistoryManager") as MockHistory, \
         patch("google.genai.Client") as MockGenAI:

        mock_history = MockHistory.return_value
        mock_history.get_full_context.return_value = ["User: 幫我畫一張橘貓"]

        engine = ChatEngine(mock_channel, "TestChat", "生成圖片", api_key="fake")

        mock_resp_tool = MagicMock()
        mock_resp_tool.text = '[TOOL_ACCESS_NEEDED, tool="image_gen", query="orange cat"]'
        mock_resp_done = MagicMock()
        mock_resp_done.text = '[CONVERSATION_ENDED, summary="done"]'

        engine.client.models.generate_content.side_effect = [mock_resp_tool, mock_resp_done]

        with patch.object(engine, '_generate_image_locally', new_callable=AsyncMock) as mock_local_gen:
            mock_local_gen.return_value = "/path/to/img.png"
            await engine.generate_and_send_reply(mock_channel.extract_messages.return_value)

            mock_local_gen.assert_called_with("orange cat")
            # Verify system notification was added to internal state
            assert any("[系統通知] 工具執行成功" in str(msg) for msg in engine.state["sent_messages"])
