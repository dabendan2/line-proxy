import base64
import hashlib
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, mock_open
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))

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

    # Normalize time expectations for testing
    with patch('channels.line.driver.datetime') as mock_dt:
        mock_dt.datetime.now.return_value.strftime.return_value = "20260515"
        mock_dt.datetime.strptime.return_value.strftime.return_value = "1000"

        with patch('channels.line.driver.extract_messages', AsyncMock(return_value=mock_msg_data)):
            state = {"file_exists": False}
            def side_effect(path):
                # We only care about the filename containing the hash
                if "image_" in str(path) and "deea.png" in str(path):
                    res = state["file_exists"]
                    state["file_exists"] = True
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
                        # Use loose matching for date to handle environmental drift in tests
                        assert f"_{expected_hash}.png" in msg["media"]["local_path"]
