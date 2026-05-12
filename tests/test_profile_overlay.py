import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import line_utils

@pytest.mark.asyncio
async def test_select_chat_handles_profile_overlay():
    mock_page = MagicMock()
    
    with patch("line_utils.is_logged_in", return_value=True), \
         patch("line_utils.CHATROOM_HEADER_SELECTOR", "header"):
        
        # Mock header to force search
        mock_header = AsyncMock()
        mock_header.is_visible.return_value = False
        mock_loc = MagicMock(); mock_loc.first = mock_header
        mock_page.locator.return_value = mock_loc

        # Mock find_chats and open_chat
        mock_chats = [{"name": "Nabi", "type": "private", "chat_id": "u1"}]
        with patch("line_utils.find_chats", return_value=mock_chats), \
             patch("line_utils.open_chat", return_value={"status": "success"}) as mock_open:
            
            result = await line_utils.select_chat(mock_page, "Nabi")
            assert result["status"] == "success"
            mock_open.assert_called_once_with(mock_page, "Nabi", "private", "u1")
