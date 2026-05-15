import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from core.engine import ChatEngine
from channels.base import BaseChannel

@pytest.mark.asyncio
async def test_image_gen_local_logic_trigger():
    """驗證當解析到 image_gen 工具時，會調用本地生成邏輯而不是遠端 API"""
    mock_channel = AsyncMock(spec=BaseChannel)
    mock_channel.extract_messages.return_value = []
    
    with patch("core.engine.HistoryManager"), \
         patch("google.genai.Client"):
        
        engine = ChatEngine(
            channel=mock_channel,
            chat_name="TestChat",
            task="Test",
            api_key="fake_key"
        )
        
        # 模擬 AI 回傳 image_gen 標籤，接著回傳結束訊息
        mock_response_tool = MagicMock()
        mock_response_tool.text = '[TOOL_ACCESS_NEEDED, tool="image_gen", query="a sunset"]'
        
        mock_response_done = MagicMock()
        mock_response_done.text = '[CONVERSATION_ENDED, summary="done"]'
        
        engine.client.models.generate_content.side_effect = [mock_response_tool, mock_response_done]
        
        with patch.object(engine, '_generate_image_locally', new_callable=AsyncMock) as mock_local_gen:
            mock_local_gen.return_value = "/tmp/local_image.png"
            await engine.generate_and_send_reply([])
            mock_local_gen.assert_called_once_with("a sunset")

@pytest.mark.asyncio
async def test_local_image_generation_execution():
    """驗證本地圖片生成的 SDK 調用邏輯"""
    mock_channel = AsyncMock(spec=BaseChannel)
    
    with patch("core.engine.HistoryManager"), \
         patch("google.genai.Client") as MockGenAI:
        
        engine = ChatEngine(channel=mock_channel, chat_name="TestChat", task="Test", api_key="fake_key")
        
        # 模擬 SDK 返回
        mock_image_response = MagicMock()
        mock_image_response.generated_images = [MagicMock()]
        mock_image_response.generated_images[0].image.save = MagicMock()
        
        engine.client.models.generate_images.return_value = mock_image_response
        
        with patch("os.makedirs"), patch("time.strftime", return_value="20260515_2110"):
            path = await engine._generate_image_locally("cat")
            
            assert "image_20260515_2110" in path
            engine.client.models.generate_images.assert_called_once()
            args, kwargs = engine.client.models.generate_images.call_args
            assert kwargs['model'] == "imagen-4.0-fast-generate-001"
            assert kwargs['prompt'] == "cat"
