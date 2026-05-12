import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import line_utils

@pytest.mark.asyncio
async def test_select_chat_avoids_groups_with_same_name():
    """
    REGRESSION TEST: Ensures that searching for 'Wayne' selects the private chat 'Wayne'
    and NOT the group 'Wayne, Nada... (4)'.
    """
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()

    # Mock the Header (initially not visible or wrong)
    mock_header = AsyncMock()
    mock_header.is_visible = AsyncMock(return_value=False)

    # Mock Search Results
    # Result 0: Group with same name start
    mock_title_0 = AsyncMock()
    mock_title_0.inner_text = AsyncMock(return_value="Wayne, Nada (4)")
    
    # Result 1: Strict match
    mock_title_1 = AsyncMock()
    mock_title_1.inner_text = AsyncMock(return_value="Wayne")
    mock_title_1.click = AsyncMock()

    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=2)
    mock_list.nth = MagicMock(side_effect=[mock_title_0, mock_title_1])

    mock_search = AsyncMock()
    mock_search.click = AsyncMock()
    mock_search.fill = AsyncMock()

    def side_effect(selector, **kwargs):
        if "Header" in selector or "header" in selector:
            l = MagicMock(); l.first = mock_header; return l
        if "Search" in selector or "搜尋" in selector:
            l = MagicMock(); l.first = mock_search; return l
        # Default fallback for new selectors (like Profile Chat button)
        l = MagicMock()
        l.first = AsyncMock()
        l.first.is_visible = AsyncMock(return_value=False)
        # Ensure the list locator is still returned for the title selector
        from config import CHATLIST_ITEM_TITLE_SELECTOR
        if selector == CHATLIST_ITEM_TITLE_SELECTOR:
            return mock_list
        return l

    mock_page.locator = MagicMock(side_effect=side_effect)

    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "Wayne")
        
        assert result["status"] == "success"
        # Crucial: Ensure it did NOT click index 0 (the group)
        mock_title_0.click.assert_not_called()
        # Crucial: Ensure it CLICKED index 1 (the strict match)
        mock_title_1.click.assert_called_once()
