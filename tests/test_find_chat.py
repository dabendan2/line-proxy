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
async def test_find_chat_success():
    """Test successful chat finding and verification."""
    mock_page = AsyncMock()
    mock_page.screenshot = AsyncMock()
    mock_res = {"status": "success", "chat_name": "楊Kurt"}
    
    with patch("playwright.async_api.async_playwright") as mock_p:
        mock_browser = AsyncMock()
        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_browser.contexts = [mock_context]
        mock_p.return_value.__aenter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("line_utils.get_line_page", return_value=mock_page), \
             patch("line_utils.is_logged_in", return_value=True), \
             patch("line_utils.find_chat", return_value=mock_res):
            
            import mcp_server
            result = await mcp_server.find_chat(chat_name="楊Kurt", port=9222)
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["chat_name"] == "楊Kurt"

@pytest.mark.asyncio
async def test_find_chat_not_found():
    """Test error handling when no match is found."""
    mock_page = AsyncMock()
    mock_page.screenshot = AsyncMock()
    mock_res = {"status": "not_found", "error": "No friend found"}
    
    with patch("playwright.async_api.async_playwright") as mock_p:
        mock_browser = AsyncMock()
        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_browser.contexts = [mock_context]
        mock_p.return_value.__aenter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("line_utils.get_line_page", return_value=mock_page), \
             patch("line_utils.is_logged_in", return_value=True), \
             patch("line_utils.find_chat", return_value=mock_res):
            
            import mcp_server
            result = await mcp_server.find_chat(chat_name="Unknown", port=9222)
            data = json.loads(result)
            assert data["status"] == "not_found"
