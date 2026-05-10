import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import line_utils

@pytest.mark.asyncio
async def test_strict_title_matching_success():
    mock_page = MagicMock()
    
    # 1. Current header
    mock_header = MagicMock()
    # 1st call (initial): False. 
    # Verification calls are not performed if initial check is false until after click.
    mock_header.is_visible = AsyncMock(return_value=False)
    
    # After click, we verify inner_text
    mock_header.inner_text = AsyncMock(return_value="dabendan.test")
    
    mock_header_locator = MagicMock()
    mock_header_locator.first = mock_header

    # 2. Sidebar Search
    mock_title_1 = MagicMock()
    mock_title_1.inner_text = AsyncMock(return_value="dabendan.test")
    
    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=1)
    mock_list.nth.return_value = mock_title_1

    # Target Item (parent)
    mock_item = MagicMock()
    mock_item.click = AsyncMock()
    mock_item.is_visible = AsyncMock(return_value=True)
    mock_item_locator = MagicMock()
    mock_item_locator.first = mock_item
    mock_title_1.locator.return_value = mock_item_locator

    def side_effect(selector, has_text=None):
        if "chatroomHeader" in selector: return mock_header_locator
        if "chatlistItem" in selector: return mock_list
        return MagicMock()

    mock_page.locator.side_effect = side_effect

    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "dabendan.test")
    
    assert result["status"] == "success"
    mock_item.click.assert_called_once()

@pytest.mark.asyncio
async def test_select_chat_not_found():
    mock_page = MagicMock()
    mock_header_locator = MagicMock()
    mock_header_locator.first.is_visible = AsyncMock(return_value=False)
    
    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=0)

    mock_page.locator.side_effect = lambda s, **k: mock_header_locator if "Header" in s else mock_list

    result = await line_utils.select_chat(mock_page, "ghost")
    assert result["status"] == "not_found"
