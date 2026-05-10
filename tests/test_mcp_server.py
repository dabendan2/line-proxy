import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# Mocks
mock_browser_manager = MagicMock()
mock_line_utils = MagicMock()
mock_engine = MagicMock()

@pytest.mark.asyncio
async def test_prepare_line_instance_tool():
    with patch("mcp_server.BrowserManager", return_value=mock_browser_manager):
        mock_browser_manager.prepare_instance.return_value = {"status": "success", "port": 9222}
        from mcp_server import prepare_line_instance
        
        result = await prepare_line_instance(port=9222)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["port"] == 9222

@pytest.mark.asyncio
async def test_find_chat_tool():
    mock_page = AsyncMock()
    mock_page.url = "chrome-extension://..."
    mock_page.evaluate = AsyncMock(return_value="clicked_directly")
    mock_page.screenshot = AsyncMock()
    
    with patch("mcp_server.async_playwright") as mock_p:
        mock_browser = AsyncMock()
        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_browser.contexts = [mock_context]
        mock_p.return_value.__aenter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("line_utils.get_line_page", return_value=mock_page):
            from mcp_server import find_chat
            result = await find_chat(chat_name="丸俊文", port=9222)
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["detail"] == "clicked_directly"

@pytest.mark.asyncio
async def test_start_proxy_task_tool():
    mock_page = AsyncMock()
    mock_engine_inst = AsyncMock()
    mock_engine_inst.state = {"final_report": "Finished"}
    mock_engine_inst.run = AsyncMock()
    
    with patch("mcp_server.async_playwright") as mock_p:
        mock_browser = AsyncMock()
        mock_context = MagicMock()
        mock_browser.contexts = [mock_context]
        mock_p.return_value.__aenter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("line_utils.get_line_page", return_value=mock_page), \
             patch("mcp_server.LineProxyEngine", return_value=mock_engine_inst), \
             patch("mcp_server.PIDLock") as mock_lock:
            
            mock_lock.return_value.acquire.return_value = True
            os.environ["GEMINI_API_KEY"] = "fake_key"
            
            from mcp_server import start_proxy_task
            result = await start_proxy_task(chat_name="丸俊文", task="test")
            data = json.loads(result)
            assert data["status"] == "completed"
            assert data["report"] == "Finished"
