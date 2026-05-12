import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Ensure the src directory is in the path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import line_utils

@pytest.mark.asyncio
async def test_list_chats_returns_chat_id():
    """Verify that list_chats returns chat_id and deduplicates by it."""
    mock_page = MagicMock()
    
    # Mock data with duplicates but same chat_id
    mock_evaluate_data = [
        {"name": "Junyu", "type": "private", "chat_id": "u123"},
        {"name": "Junyu (Active)", "type": "private", "chat_id": "u123"}, # Duplicate ID
        {"name": "Group A", "type": "group", "chat_id": "c456"}
    ]
    
    with patch("line_utils.is_logged_in", return_value=True), \
         patch.object(mock_page, "evaluate", AsyncMock(return_value=mock_evaluate_data)):
        
        # Navigation mocks
        mock_page.locator = MagicMock()
        mock_page.locator.return_value.first = AsyncMock()
        mock_page.locator.return_value.first.is_visible.return_value = True
        mock_page.keyboard.press = AsyncMock()
        
        result = await line_utils.list_chats(mock_page, "Junyu")
        
        # Ensure it's not an error dict
        assert isinstance(result, list), f"Expected list, got {result}"
        # Should be deduplicated to 2 items
        assert len(result) == 2
        ids = [r["chat_id"] for r in result]
        assert "u123" in ids
        assert "c456" in ids
        assert len(set(ids)) == 2

@pytest.mark.asyncio
async def test_open_chat_uses_chat_id():
    """Verify that open_chat prioritizes clicking by chat_id."""
    mock_page = MagicMock()
    
    # Mock locator for chat_id
    mock_id_locator = AsyncMock()
    mock_id_locator.is_visible.return_value = True
    
    # Mock locator for fallback
    mock_fallback_locator = AsyncMock()
    
    # Mock verification elements
    mock_header = AsyncMock()
    mock_header.is_visible.return_value = True
    mock_header.inner_text.return_value = "Junyu"
    mock_input = AsyncMock()
    mock_input.is_visible.return_value = True

    def side_effect(selector):
        m = MagicMock()
        # Default first to an AsyncMock that is not visible
        m.first = AsyncMock()
        m.first.is_visible.return_value = False
        
        if 'data-mid="u123"' in selector:
            m.first = mock_id_locator
            return m
        elif "chatroomHeader" in selector:
            m.first = mock_header
            return m
        elif "message_input" in selector or "contenteditable" in selector:
            m.first = mock_input
            return m
        return m

    mock_page.locator.side_effect = side_effect
    
    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.open_chat(mock_page, "Junyu", "private", chat_id="u123")
        
        if result["status"] == "error":
            print(f"DEBUG: Error result: {result}")
        assert result["status"] == "success"
        # Verify chat_id locator was used and clicked
        mock_id_locator.click.assert_called_once()

@pytest.mark.asyncio
async def test_select_chat_passes_chat_id():
    """Verify that select_chat correctly passes chat_id to open_chat."""
    mock_page = MagicMock()
    
    mock_chats = [
        {"name": "Junyu", "type": "private", "chat_id": "u123"}
    ]
    
    with patch("line_utils.is_logged_in", return_value=True), \
         patch("line_utils.CHATROOM_HEADER_SELECTOR", "header"), \
         patch("line_utils.MESSAGE_INPUT_SELECTOR", "input"), \
         patch("line_utils.list_chats", return_value=mock_chats), \
         patch("line_utils.open_chat", return_value={"status": "success"}) as mock_open:
        
        # Force search by making header mismatch
        mock_header = AsyncMock()
        mock_header.is_visible.return_value = False
        mock_page.locator.return_value.first = mock_header
        
        result = await line_utils.select_chat(mock_page, "Junyu", chat_id="u123")
        
        assert result["status"] == "success"
        mock_open.assert_called_once()
        _, kwargs = mock_open.call_args
        # Fourth positional or keyword arg should be chat_id
        assert mock_open.call_args[0][3] == "u123"
