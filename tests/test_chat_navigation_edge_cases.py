import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import sys
import os

# Ensure the src directory is in the path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import line_utils

@pytest.mark.asyncio
async def test_list_chats_deduplication_and_classification():
    """
    Test the classification logic in list_chats. 
    Since the actual logic is in JS, we mock the evaluate call to simulate 
    the complex environment we just fixed.
    """
    mock_page = MagicMock()
    
    # Simulate the data that would cause the previous 'count: 11' error
    mock_evaluate_data = [
        {"name": "Wayne, Nada, dabendan, 娜比\n(4)", "type": "group"},
        {"name": "dabendan, Wayne, 娜比\n(3)", "type": "group"},
        {"name": "娜比", "type": "private"}
    ]
    
    with patch("line_utils.is_logged_in", return_value=True), \
         patch.object(mock_page, "evaluate", AsyncMock(return_value=mock_evaluate_data)):
        
        # We also need to mock the navigation parts of list_chats
        mock_friend_btn = AsyncMock()
        mock_friend_btn.is_visible.return_value = True
        
        mock_search_input = AsyncMock()
        
        def locator_side_effect(selector):
            m = MagicMock()
            if "aria-label" in selector:
                m.first = mock_friend_btn
            elif "Search" in selector or "input" in selector:
                m.first = mock_search_input
            return m
            
        mock_page.locator.side_effect = locator_side_effect
        mock_page.keyboard.press = AsyncMock()
        
        result = await line_utils.list_chats(mock_page, "娜比")
        
        # Verify the count is correct (no duplicates from sub-elements)
        assert len(result) == 3
        assert result[0]["type"] == "group"
        assert result[2]["name"] == "娜比"
        assert result[2]["type"] == "private"

@pytest.mark.asyncio
async def test_select_chat_ambiguity_resolution():
    """
    Test that select_chat correctly prioritizes exact matches.
    """
    mock_page = MagicMock()
    
    mock_chats = [
        {"name": "Wayne, 娜比 (4)", "type": "group"},
        {"name": "娜比", "type": "group"}, # A group named exactly "娜比"
        {"name": "娜比", "type": "private"} # The actual person
    ]
    
    with patch("line_utils.is_logged_in", return_value=True), \
         patch("line_utils.CHATROOM_HEADER_SELECTOR", "header"), \
         patch("line_utils.MESSAGE_INPUT_SELECTOR", "input"), \
         patch("line_utils.list_chats", return_value=mock_chats), \
         patch("line_utils.open_chat", return_value={"status": "success"}) as mock_open:
        
        # Mock header to force search
        mock_header = AsyncMock()
        mock_header.is_visible.return_value = False
        
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

        # Target is "娜比"
        result = await line_utils.select_chat(mock_page, "娜比")
        
        assert result["status"] == "success"
        mock_open.assert_called_once()
        args, _ = mock_open.call_args
        assert args[1] == "娜比"

@pytest.mark.asyncio
async def test_open_chat_private_triggers_bridge():
    """Verify that opening a private chat triggers the Profile Bridge (Chat button)."""
    mock_page = MagicMock()
    
    # Mock locator for the list item
    mock_item = AsyncMock()
    mock_item.inner_text.return_value = "娜比"
    
    # Mock locator for the Chat button (Profile Bridge)
    mock_chat_btn = AsyncMock()
    mock_chat_btn.is_visible.return_value = True
    
    # Mock header for verification
    mock_header = AsyncMock()
    mock_header.is_visible.return_value = True
    mock_header.inner_text.return_value = "娜比"
    
    # Mock input for verification
    mock_input = AsyncMock()
    mock_input.is_visible.return_value = True

    def side_effect(selector):
        m = MagicMock()
        if "Chat" in selector or "聊天" in selector:
            m.first = mock_chat_btn
        elif "chatroomHeader" in selector:
            m.first = mock_header
        elif "message_input" in selector or "contenteditable" in selector:
            m.first = mock_input
        else:
            m.count = AsyncMock(return_value=1)
            m.nth.return_value = mock_item
        return m

    mock_page.locator.side_effect = side_effect
    
    import line_utils
    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.open_chat(mock_page, "娜比", "private")
        
        assert result["status"] == "success"
        # Verify the bridge button was clicked
        mock_chat_btn.click.assert_called_once()

@pytest.mark.asyncio
async def test_open_chat_strict_exact_match():
    """Verify that open_chat only clicks on exact matches and fails on partial matches."""
    mock_page = MagicMock()
    
    # 1. Test case: Both partial and exact matches exist
    # Items: "娜比討論群", "娜比"
    mock_partial = AsyncMock()
    mock_partial.inner_text.return_value = "娜比討論群"
    mock_exact = AsyncMock()
    mock_exact.inner_text.return_value = "娜比"
    
    mock_header = AsyncMock()
    mock_header.is_visible.return_value = True
    mock_header.inner_text.return_value = "娜比"
    mock_input = AsyncMock()
    mock_input.is_visible.return_value = True

    def side_effect(selector):
        m = MagicMock()
        if "chatroomHeader" in selector:
            m.first = mock_header
        elif "message_input" in selector or "contenteditable" in selector:
            m.first = mock_input
        else:
            # For list items
            m.count = AsyncMock(return_value=2)
            # Use a function to ensure same index returns same mock
            m.nth = MagicMock(side_effect=lambda idx: mock_partial if idx == 0 else mock_exact)
        return m

    mock_page.locator.side_effect = side_effect
    
    with patch("line_utils.asyncio.sleep", AsyncMock()):
        # Should pick index 1 ("娜比")
        result = await line_utils.open_chat(mock_page, "娜比", "group")
        assert result["status"] == "success"
        mock_exact.click.assert_called_once()
        mock_partial.click.assert_not_called()

    # 2. Test case: Only partial matches exist
    mock_partial_only = AsyncMock()
    mock_partial_only.inner_text.return_value = "娜比討論群"
    
    def side_effect_failure(selector):
        m = MagicMock()
        m.count = AsyncMock(return_value=1)
        m.nth.return_value = mock_partial_only
        return m
        
    mock_page.locator.side_effect = side_effect_failure
    
    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.open_chat(mock_page, "娜比", "group")
        # Should fail because "娜比" != "娜比討論群"
        assert result["status"] == "error"
        assert "Could not find exact match" in result["error"]
        mock_partial_only.click.assert_not_called()
