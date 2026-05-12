import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import line_utils

@pytest.mark.asyncio
async def test_select_chat_avoids_groups_with_same_name():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value=[])
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()

    # find_chats returns multiple, but select_chat should pick the exact match
    mock_chats = [
        {"name": "Wayne, Nada (4)", "type": "group", "chat_id": "c1"},
        {"name": "Wayne", "type": "private", "chat_id": "u1"}
    ]

    with patch("line_utils.is_logged_in", return_value=True), \
         patch("line_utils.CHATROOM_HEADER_SELECTOR", "header"), \
         patch("line_utils.find_chats", return_value=mock_chats), \
         patch("line_utils.open_chat", return_value={"status": "success"}) as mock_open:

        # Mock header to return something else first to force search
        mock_header = AsyncMock()
        mock_header.is_visible.return_value = False
        mock_loc = MagicMock()
        mock_loc.first = mock_header
        mock_page.locator.return_value = mock_loc

        result = await line_utils.select_chat(mock_page, "Wayne")

        assert result["status"] == "success"
        # Verify open_chat was called with the exact match
        mock_open.assert_called_once_with(mock_page, "Wayne", "private", "u1")
