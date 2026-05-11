import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import line_utils

@pytest.mark.asyncio
async def test_strict_title_matching_already_selected():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()
    
    mock_header = AsyncMock()
    mock_header.is_visible = AsyncMock(return_value=True)
    mock_header.inner_text = AsyncMock(return_value="dabendan.test")
    
    mock_locator = MagicMock()
    mock_locator.first = mock_header
    mock_page.locator = MagicMock(return_value=mock_locator)

    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "dabendan.test")
    assert result["status"] == "success"

@pytest.mark.asyncio
async def test_select_chat_with_search_success():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()

    mock_header = AsyncMock()
    mock_header.is_visible = AsyncMock(return_value=False)
    
    mock_title = AsyncMock()
    mock_title.inner_text = AsyncMock(return_value="dabendan.test")
    mock_title.click = AsyncMock()

    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=1)
    mock_list.nth = MagicMock(return_value=mock_title)

    mock_search = AsyncMock()
    mock_search.click = AsyncMock()
    mock_search.fill = AsyncMock()

    def side_effect(selector, **kwargs):
        if "Header" in selector or "header" in selector:
            l = MagicMock(); l.first = mock_header; return l
        if "Search" in selector or "搜尋" in selector:
            l = MagicMock(); l.first = mock_search; return l
        return mock_list

    mock_page.locator = MagicMock(side_effect=side_effect)

    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "dabendan.test")
    
    assert result["status"] == "success"
    mock_title.click.assert_called_once_with(force=True)

@pytest.mark.asyncio
async def test_select_chat_not_found():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()

    mock_header = AsyncMock()
    mock_header.is_visible = AsyncMock(return_value=False)
    
    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=0)

    mock_search = AsyncMock()
    mock_search.click = AsyncMock()
    mock_search.fill = AsyncMock()

    def side_effect(selector, **kwargs):
        if "Header" in selector or "header" in selector:
            l = MagicMock(); l.first = mock_header; return l
        if "Search" in selector or "搜尋" in selector:
            l = MagicMock(); l.first = mock_search; return l
        return mock_list

    mock_page.locator = MagicMock(side_effect=side_effect)

    with patch("line_utils.asyncio.sleep", AsyncMock()):
        result = await line_utils.select_chat(mock_page, "ghost")
    
    assert result["status"] == "not_found"
