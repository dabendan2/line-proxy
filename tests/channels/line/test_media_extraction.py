import pytest
import os
import hashlib
import base64
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
import datetime

# Mocking the constants before importing LineChannel
with patch('utils.config.FILE_CACHE_DIR', Path("/tmp/media")):
    from channels.line.driver import LineChannel

@pytest.mark.asyncio
async def test_line_channel_media_download_logic():
    """
    Test that LineChannel.extract_messages correctly identifies media,
    downloads it to the local media directory, and updates the message object.
    """
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    
    mock_msg_data = [
        {
            "id": "msg_123",
            "sender": "Wayne",
            "text": "[Image]",
            "timestamp": "10:00 AM",
            "date": "2026/05/15",
            "media": {
                "type": "image",
                "url": "blob:chrome-extension://abc/123"
            }
        }
    ]
    
    with patch('channels.line.driver.datetime') as mock_dt:
        mock_dt.datetime.now.return_value.strftime.return_value = "20260515"
        mock_dt.datetime.strptime.return_value.strftime.return_value = "1000"
        
        with patch('channels.line.driver.extract_messages', AsyncMock(return_value=mock_msg_data)):
            # Stateful mock for os.path.exists
            # Initially False, but should return True after the code "writes" the file
            state = {"file_exists": False}
            def side_effect(path):
                if "image_20260515_1000" in str(path):
                    res = state["file_exists"]
                    state["file_exists"] = True # Set to True for subsequent calls
                    return res
                return True

            with patch('os.path.exists', side_effect=side_effect):
                with patch('os.makedirs'):
                    m_open = mock_open()
                    with patch('builtins.open', m_open):
                        mock_b64 = base64.b64encode(b"fake_image_data").decode('utf-8')
                        mock_page.evaluate.return_value = mock_b64
                        
                        channel = LineChannel(page=mock_page, owner_name="Owner")
                        results = await channel.extract_messages(limit=1)
                        
                        assert len(results) == 1
                        msg = results[0]
                        assert "local_path" in msg["media"]
                        
                        expected_hash = hashlib.md5("msg_123".encode()).hexdigest()[:4]
                        assert f"image_20260515_1000_{expected_hash}.png" in msg["media"]["local_path"]
                        
                        handle = m_open()
                        handle.write.assert_called_with(b"fake_image_data")

@pytest.mark.asyncio
async def test_line_channel_skips_download_if_file_exists():
    """
    Test that LineChannel.extract_messages does NOT re-download if the file already exists.
    """
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    
    mock_msg_data = [
        {
            "id": "msg_456",
            "sender": "Wayne",
            "text": "[Image]",
            "timestamp": "11:00 AM",
            "date": "2026/05/15",
            "media": {
                "type": "image",
                "url": "blob:chrome-extension://abc/456"
            }
        }
    ]
    
    with patch('channels.line.driver.datetime') as mock_dt:
        mock_dt.datetime.now.return_value.strftime.return_value = "20260515"
        mock_dt.datetime.strptime.return_value.strftime.return_value = "1100"
        
        with patch('channels.line.driver.extract_messages', AsyncMock(return_value=mock_msg_data)):
            with patch('os.path.exists', return_value=True):
                with patch('os.makedirs'):
                    channel = LineChannel(page=mock_page, owner_name="Owner")
                    results = await channel.extract_messages(limit=1)
                    
                    assert len(results) == 1
                    msg = results[0]
                    assert "local_path" in msg["media"]
                    assert mock_page.evaluate.call_count == 0
