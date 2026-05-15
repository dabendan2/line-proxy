import pytest
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch
from core.engine import ChatEngine

@patch('os.path.exists', return_value=True)
@patch('os.path.getmtime', return_value=time.time())
@patch('google.genai.Client')
def test_prompt_includes_file_resources(mock_genai, mock_mtime, mock_exists):
    """
    Test that the prompt correctly includes information about available files.
    """
    mock_channel = MagicMock()
    engine = ChatEngine(
        channel=mock_channel,
        chat_name="Test",
        task="Test Task",
        api_key="fake_key"
    )
    
    msgs = [
        {
            "sender": "User",
            "text": "Check this",
            "timestamp": "12:00",
            "media": {
                "type": "file",
                "name": "data.zip",
                "local_path": "/home/ubuntu/file-cache/test/data.zip"
            }
        }
    ]
    
    prompt = engine._build_prompt(msgs, ["User: Check this"])
    
    assert "## 可用的本地檔案資源 ##" in prompt
    assert "file: data.zip, 路徑: /home/ubuntu/file-cache/test/data.zip" in prompt
    assert "terminal" in prompt

@patch('os.path.exists', return_value=True)
@patch('os.path.getmtime', return_value=time.time())
@patch('google.genai.Client')
def test_prompt_includes_image_resources(mock_genai, mock_mtime, mock_exists):
    """
    Test that the prompt correctly includes information about available images.
    """
    mock_channel = MagicMock()
    engine = ChatEngine(
        channel=mock_channel,
        chat_name="Test",
        task="Test Task",
        api_key="fake_key"
    )
    
    msgs = [
        {
            "sender": "User",
            "text": "[Image]",
            "timestamp": "12:05",
            "media": {
                "type": "image",
                "local_path": "/home/ubuntu/file-cache/test/image.png"
            }
        }
    ]
    
    prompt = engine._build_prompt(msgs, ["User: [Image]"])
    
    assert "## 可用的本地檔案資源 ##" in prompt
    assert "image: image.png, 路徑: /home/ubuntu/file-cache/test/image.png" in prompt
    assert "vision_analyze" in prompt
