import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import line_utils

@pytest.mark.asyncio
async def test_select_chat_handles_profile_overlay():
    """
    Test that select_chat clicks the 'Chat' button if a profile overlay appears.
    """
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()
    
    # 1. Mock Header (not currently in the right chat)
    mock_header = AsyncMock()
    mock_header.is_visible = AsyncMock(return_value=False)
    
    # 2. Mock Search Input
    mock_search = AsyncMock()
    mock_search.click = AsyncMock()
    mock_search.fill = AsyncMock()
    
    # 3. Mock Chat List Item
    mock_title = AsyncMock()
    mock_title.inner_text = AsyncMock(return_value="Nabi")
    mock_title.click = AsyncMock()
    
    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=1)
    mock_list.nth = MagicMock(return_value=mock_title)
    
    # 4. Mock Profile 'Chat' Button
    # We'll make it visible for the first selector to simulate a match
    mock_chat_btn = AsyncMock()
    mock_chat_btn.is_visible = AsyncMock(side_effect=[True, False, False, False, False, False])
    mock_chat_btn.click = AsyncMock()
    
    def side_effect(selector, **kwargs):
        if "chatroomHeader" in selector:
            l = MagicMock(); l.first = mock_header; return l
        if "Search" in selector or "搜尋" in selector:
            l = MagicMock(); l.first = mock_search; return l
        if "has-text(\"Chat\")" in selector or "has-text(\"聊天\")" in selector:
            l = MagicMock(); l.first = mock_chat_btn; return l
        return mock_list

    mock_page.locator = MagicMock(side_effect=side_effect)
    
    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "Nabi")
        
    assert result["status"] == "success"
    # Verify that the profile chat button was clicked
    mock_chat_btn.click.assert_called_once()
    # Verify the initial contact was also clicked
    mock_title.click.assert_called_once_with(force=True)
