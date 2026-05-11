import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import line_utils

@pytest.mark.asyncio
async def test_strict_title_matching_success():
    mock_page = AsyncMock()
    
    # Mocking new interactions in select_chat
    mock_page.evaluate = AsyncMock()
    mock_page.keyboard.press = AsyncMock()
    
    # 1. Current header
    mock_header = AsyncMock()
    mock_header.is_visible = AsyncMock(return_value=False)
    mock_header.inner_text = AsyncMock(return_value="dabendan.test")
    
    mock_header_locator = MagicMock()
    mock_header_locator.first = mock_header
    
    # 2. Sidebar Search Results
    mock_title_1 = AsyncMock()
    mock_title_1.inner_text = AsyncMock(return_value="dabendan.test")
    mock_title_1.click = AsyncMock() # Now clicking target_item directly
    
    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=1)
    mock_list.nth.return_value = mock_title_1

    # Search Input Mock
    mock_search = AsyncMock()
    mock_search_loc = MagicMock()
    mock_search_loc.first = mock_search

    def side_effect(selector, **kwargs):
        if "chatroomHeader" in selector: return mock_header_locator
        if "chatlistItem" in selector: return mock_list
        if "Search" in selector or "搜尋" in selector: return mock_search_loc
        return MagicMock()

    mock_page.locator.side_effect = side_effect

    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "dabendan.test")
    
    assert result["status"] == "success"
    # In new logic, target_item is title_locator.nth(i)
    mock_title_1.click.assert_called_once()

@pytest.mark.asyncio
async def test_select_chat_not_found():
    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock()
    mock_page.keyboard.press = AsyncMock()

    mock_header_locator = MagicMock()
    mock_header_locator.first.is_visible = AsyncMock(return_value=False)
    
    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=0)

    mock_search = AsyncMock()
    mock_search_loc = MagicMock()
    mock_search_loc.first = mock_search

    def side_effect(selector, **kwargs):
        if "Header" in selector: return mock_header_locator
        if "Search" in selector: return mock_search_loc
        return mock_list

    mock_page.locator.side_effect = side_effect

    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "ghost")
    assert result["status"] == "not_found"
