import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import sys
import os

# Ensure the src directory is in the path
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

@pytest.mark.asyncio
async def test_find_chats_success():
    """Test successful chat listing."""
    mock_page = MagicMock()
    mock_chats = [{"name": "Junyu", "type": "private"}]
    
    with patch("line_utils.find_chats", return_value=mock_chats):
        import line_utils
        result = await line_utils.find_chats(mock_page, "Junyu")
        assert len(result) == 1
        assert result[0]["name"] == "Junyu"
        assert result[0]["type"] == "private"

@pytest.mark.asyncio
async def test_open_chat_success():
    """Test successful chat opening."""
    mock_page = MagicMock()
    mock_page.locator = MagicMock()
    
    # Verification mocks
    mock_header = AsyncMock()
    mock_header.is_visible.return_value = True
    mock_header.inner_text.return_value = "Junyu"
    
    mock_input = AsyncMock()
    mock_input.is_visible.return_value = True

    # Mock Chat button (Profile Bridge) - it should not be visible by default to skip it
    mock_chat_btn = AsyncMock()
    mock_chat_btn.is_visible.return_value = False

    # Mock chat_id locator
    mock_id_locator = AsyncMock()
    mock_id_locator.is_visible.return_value = True
    
    # This is tricky because open_chat calls locator multiple times with different selectors
    def locator_side_effect(selector):
        m = MagicMock()
        if "data-mid" in selector:
            m.first = mock_id_locator
        elif "chatroomHeader" in selector:
            m.first = mock_header
        elif "message_input" in selector or "contenteditable" in selector:
            m.first = mock_input
        elif "Chat" in selector or "聊天" in selector:
            m.first = mock_chat_btn
        else:
            m.count = AsyncMock(return_value=1)
            m.nth.return_value.inner_text = AsyncMock(return_value="Junyu")
            m.nth.return_value.scroll_into_view_if_needed = AsyncMock()
            m.nth.return_value.click = AsyncMock()
        return m

    mock_page.locator.side_effect = locator_side_effect
    
    import line_utils
    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.open_chat(mock_page, "Junyu", "group", chat_id="u123") # group skips profile bridge
        assert result["status"] == "success"
        assert result["chat_name"] == "Junyu"

@pytest.mark.asyncio
async def test_select_chat_idempotency():
    """Test that select_chat doesn't re-open if already on the chat."""
    mock_page = MagicMock()
    mock_page.locator = MagicMock()
    
    # Mock is_logged_in
    with patch("line_utils.is_logged_in", return_value=True), \
         patch("line_utils.CHATROOM_HEADER_SELECTOR", "header"), \
         patch("line_utils.MESSAGE_INPUT_SELECTOR", "input"):
        
        # Mock header text to match target
        mock_header = AsyncMock()
        mock_header.is_visible.return_value = True
        mock_header.inner_text.return_value = "Junyu"
        
        mock_input = AsyncMock()
        mock_input.is_visible.return_value = True
        
        def locator_side_effect(selector):
            m = MagicMock()
            if selector == "header":
                m.first = mock_header
            elif selector == "input":
                m.first = mock_input
            return m
            
        mock_page.locator.side_effect = locator_side_effect
        
        import line_utils
        # We need to mock find_chat/open_chat to ensure they are NOT called
        with patch("line_utils.find_chats") as mock_find, \
             patch("line_utils.open_chat") as mock_open:
            
            result = await line_utils.select_chat(mock_page, "Junyu")
            assert result["status"] == "success"
            assert "already selected" in result["info"]
            mock_find.assert_not_called()
            mock_open.assert_not_called()
