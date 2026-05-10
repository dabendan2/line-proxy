import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import sys
import os
from pathlib import Path

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
            result = await find_chat(chat_name="test_chat", port=9222)
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["detail"] == "clicked_directly"

@pytest.mark.asyncio
async def test_send_line_message_tool():
    mock_page = AsyncMock()
    
    with patch("mcp_server.async_playwright") as mock_p:
        mock_browser = AsyncMock()
        mock_context = MagicMock()
        mock_browser.contexts = [mock_context]
        mock_p.return_value.__aenter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("line_utils.get_line_page", return_value=mock_page), \
             patch("line_utils.select_chat", return_value={"status": "success"}), \
             patch("line_utils.send_message", return_value=AsyncMock()):
            
            from mcp_server import send_line_message
            result = await send_line_message(chat_name="test_chat", text="hello")
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["chat"] == "test_chat"
            assert data["text"] == "hello"

@pytest.mark.asyncio
async def test_get_line_messages_tool():
    mock_page = AsyncMock()
    mock_msgs = [
        {"text": "msg1", "is_self_dom": False, "timestamp": "10:00"},
        {"text": "msg2", "is_self_dom": True, "timestamp": "10:01"}
    ]
    
    with patch("mcp_server.async_playwright") as mock_p:
        mock_browser = AsyncMock()
        mock_context = MagicMock()
        mock_browser.contexts = [mock_context]
        mock_p.return_value.__aenter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("line_utils.get_line_page", return_value=mock_page), \
             patch("line_utils.select_chat", return_value={"status": "success"}), \
             patch("line_utils.extract_messages", return_value=mock_msgs):
            
            from mcp_server import get_line_messages
            result = await get_line_messages(chat_name="test_chat", limit=1)
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["count"] == 1
            assert data["messages"][0]["text"] == "msg2"

@pytest.mark.asyncio
async def test_start_proxy_task_tool_background():
    with patch("mcp_server.subprocess.Popen") as mock_popen, \
         patch("mcp_server.PIDLock") as mock_lock, \
         patch("builtins.open", MagicMock()):
        
        mock_lock.return_value.acquire.return_value = True
        mock_popen.return_value.pid = 1234
        os.environ["GEMINI_API_KEY"] = "fake_key"
        
        from mcp_server import start_proxy_task
        result = await start_proxy_task(chat_name="test_chat", task="test_task")
        data = json.loads(result)
        
        assert data["status"] == "started"
        assert data["pid"] == 1234
        assert mock_popen.called

@pytest.mark.asyncio
async def test_get_task_status_tool():
    with patch("mcp_server.PIDLock") as mock_lock, \
         patch("mcp_server.Path.exists", return_value=True), \
         patch("builtins.open", MagicMock()) as mock_open:
        
        # Mock file read
        mock_open.return_value.__enter__.return_value.readlines.return_value = ["line1\n", "line2\n"]
        
        # Test running state (lock held)
        mock_lock.return_value.acquire.return_value = False
        from mcp_server import get_task_status
        result = await get_task_status(chat_name="test_chat")
        data = json.loads(result)
        assert data["status"] == "running"
        assert "line1" in data["last_log"]
        
        # Test not running state (lock acquired)
        mock_lock.return_value.acquire.return_value = True
        result = await get_task_status(chat_name="test_chat")
        data = json.loads(result)
        assert data["status"] == "not_running"
