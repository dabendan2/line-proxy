import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
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
    mock_client.models.generate_content.return_value = mock_ai_resp
    
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
    
    # Verify the channel was notified about tool execution
    calls = mock_channel.send_message.call_args_list
    sent_texts = [call.args[0] for call in calls]
    assert any("[系統] 正在執行工具: terminal..." in t for t in sent_texts)

@pytest.mark.asyncio
@patch('google.genai.Client')
async def test_ai_proposes_vision_analyze_for_image(mock_genai_class):
    """
    Verify that when the prompt contains an image, the AI logic processes it.
    We mock the AI response to return a vision_analyze tool request.
    """
    mock_client = mock_genai_class.return_value
    mock_channel = AsyncMock()
    
    engine = ChatEngine(
        channel=mock_channel,
        chat_name="Test",
        task="分析圖片",
        api_key="fake_key"
    )
    
    # Mock AI response to trigger vision_analyze
    mock_ai_resp = MagicMock()
    mock_ai_resp.text = '[TOOL_ACCESS_NEEDED, tool="vision_analyze", query="這張圖畫了什麼"]'
    mock_client.models.generate_content.return_value = mock_ai_resp
    
    # Mock execute_hermes_tool
    engine.execute_hermes_tool = AsyncMock(return_value="It is a dog.")

    msgs = [
        {
            "sender": "User",
            "text": "[照片]",
            "media": {
                "type": "image",
                "local_path": "/home/ubuntu/chat-agent/file-cache/test/image.png"
            }
        }
    ]
    
    await engine.generate_and_send_reply(msgs)
    
@pytest.mark.asyncio
@patch('google.genai.Client')
async def test_ai_ignores_irrelevant_file_requests(mock_genai_class):
    """
    Verify that the AI does NOT use tools for files that are irrelevant to its task.
    Task: Analyze dog images.
    User action: Uploads a text file and asks to summarize.
    Result: AI should NOT call read_file or terminal on that file.
    """
    mock_client = mock_genai_class.return_value
    mock_channel = AsyncMock()
    
    engine = ChatEngine(
        channel=mock_channel,
        chat_name="Test",
        task="請分析對方傳來的狗狗圖片，並告訴我品種。",
        api_key="fake_key"
    )
    
    # Mock AI response: It should either say it can't do it or wait for user input.
    # It should NOT contain [TOOL_ACCESS_NEEDED]
    mock_ai_resp = MagicMock()
    mock_ai_resp.text = "對不起，我的任務是分析狗狗圖片，無法幫您整理文字檔案。[WAIT_FOR_USER_INPUT]"
    mock_client.models.generate_content.return_value = mock_ai_resp
    
    msgs = [
        {
            "sender": "User",
            "text": "幫我整理這個檔案",
            "media": {
                "type": "file",
                "name": "notes.txt",
                "local_path": "/home/ubuntu/chat-agent/file-cache/test/notes.txt"
            }
        }
    ]
    
    await engine.generate_and_send_reply(msgs)
    
    # Verify no tool execution was triggered
    calls = mock_channel.send_message.call_args_list
    sent_texts = [call.args[0] for call in calls]
    
    # AI should not have sent the [系統] tool notification
    assert not any("[系統] 正在執行工具" in t for t in sent_texts), f"AI incorrectly triggered a tool for an irrelevant file. Sent: {sent_texts}"
    # AI should have sent its reply text
    assert any("無法" in t or "任務" in t for t in sent_texts)
