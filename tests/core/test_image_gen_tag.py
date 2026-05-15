import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# 確保 PYTHONPATH 包含 src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from core.engine import ChatEngine
from channels.base import BaseChannel

@pytest.mark.asyncio
async def test_image_gen_tag_generation():
    """驗證當任務需要生成圖片時，AI 能正確輸出 [TOOL_ACCESS_NEEDED, tool="image_gen", ...] 標籤"""
    mock_channel = AsyncMock(spec=BaseChannel)
    mock_channel.extract_messages.return_value = [
        {"sender": "User", "text": "幫我畫一張可愛的橘貓圖片"}
    ]
    
    with patch("core.engine.HistoryManager") as MockHistory, \
         patch("google.genai.Client") as MockGenAI:
        
        mock_history = MockHistory.return_value
        mock_history.get_full_context.return_value = ["User: 幫我畫一張可愛的橘貓圖片"]
        
        engine = ChatEngine(
            channel=mock_channel,
            chat_name="TestChat",
            task="根據使用者需求生成圖片",
            api_key="fake_key"
        )
        
        # 模擬 Gemini Client response
        # 第一回傳 tool 標籤，第二回傳結束訊息以避免無窮遞迴
        mock_response_tool = MagicMock()
        mock_response_tool.text = '好的，我這就為您生成一張可愛的橘貓圖片。[TOOL_ACCESS_NEEDED, tool="image_gen", query="cute orange cat"]'
        
        mock_response_done = MagicMock()
        mock_response_done.text = '圖片已完成。[CONVERSATION_ENDED, summary="Generated cat image"]'
        
        engine.client.models.generate_content.side_effect = [mock_response_tool, mock_response_done]
        
        # 攔截本地生成邏輯
        with patch.object(engine, '_generate_image_locally', new_callable=AsyncMock) as mock_local_gen:
            mock_local_gen.return_value = "/path/to/generated_image.png"
            
            await engine.generate_and_send_reply(mock_channel.extract_messages.return_value)
            
            # 檢查 _generate_image_locally 是否被調用
            mock_local_gen.assert_called_with("cute orange cat")
            
            # 驗證是否傳送了系統通知
            mock_channel.send_message.assert_any_call("[系統] 正在執行工具: image_gen...")
