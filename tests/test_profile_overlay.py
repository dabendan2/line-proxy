import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import line_utils

@pytest.mark.asyncio
async def test_select_chat_handles_profile_overlay():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value=[])
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()

    mock_header = AsyncMock()
    mock_header.is_visible = AsyncMock(side_effect=[False, True, True])
    mock_header.inner_text = AsyncMock(return_value="Nabi")

    mock_title = AsyncMock()
    mock_title.inner_text = AsyncMock(return_value="Nabi")
    mock_title.click = AsyncMock()

    mock_chat_btn = AsyncMock()
    mock_chat_btn.is_visible = AsyncMock(return_value=True)
    mock_chat_btn.click = AsyncMock()

    mock_list = MagicMock()
    mock_list.count = AsyncMock(return_value=1)
    mock_list.nth = MagicMock(return_value=mock_title)
    mock_list.first = mock_title

    def side_effect(selector, **kwargs):
        l = MagicMock()
        if "Header" in selector or "header" in selector: l.first = mock_header; return l
        if "Friend" in selector or "aria-label" in selector: 
            f = AsyncMock(); f.is_visible = AsyncMock(return_value=True); l.first = f; return l
        if "Search" in selector or "搜尋" in selector or "input" in selector:
            s = AsyncMock(); s.is_visible = AsyncMock(return_value=True); l.first = s; return l
        if "Chat" in selector or "聊天" in selector:
            l.first = mock_chat_btn; return l
        if "message_input" in selector or "contenteditable" in selector:
            i = AsyncMock(); i.is_visible = AsyncMock(return_value=True); l.first = i; return l
        return mock_list

    mock_page.locator = MagicMock(side_effect=side_effect)
    mock_page.get_by_text = MagicMock(return_value=mock_title)

    with patch("line_utils.asyncio.sleep", AsyncMock()), \
         patch("line_utils.is_logged_in", return_value=True):
        result = await line_utils.select_chat(mock_page, "Nabi")
        assert result["status"] == "success"
        mock_title.click.assert_called_once()
        mock_chat_btn.click.assert_called_once()
