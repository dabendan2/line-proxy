import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import sys
import os

# Ensure the src directory is in the path
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Mocks
mock_browser_manager = MagicMock()
mock_line_utils = MagicMock()

@pytest.mark.asyncio
async def test_prepare_line_instance_tool():
    with patch("browser_manager.BrowserManager", return_value=mock_browser_manager):
        mock_browser_manager.prepare_instance.return_value = {"status": "success", "port": 9222}
        import mcp_server
        
        result = await mcp_server.prepare_line_instance(port=9222)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["port"] == 9222

@pytest.mark.asyncio
async def test_list_chats_tool():
    mock_page = AsyncMock()
    mock_page.screenshot = AsyncMock()
    mock_chats = [{"name": "Junyu", "type": "private"}, {"name": "Group A", "type": "group"}]
    
    with patch("playwright.async_api.async_playwright") as mock_p:
        mock_browser = AsyncMock()
        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_browser.contexts = [mock_context]
        mock_p.return_value.__aenter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("line_utils.get_line_page", return_value=mock_page), \
             patch("line_utils.is_logged_in", return_value=True), \
             patch("line_utils.list_chats", return_value=mock_chats):
            
            import mcp_server
            # Reload to ensure new tools are registered if needed, though import is fine
            result = await mcp_server.list_chats(keyword="test", port=9222)
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["count"] == 2
            assert data["chats"][0]["name"] == "Junyu"

@pytest.mark.asyncio
async def test_open_chat_tool():
    mock_page = AsyncMock()
    mock_page.screenshot = AsyncMock()
    mock_res = {"status": "success", "chat_name": "Junyu", "type": "private"}
    
    with patch("playwright.async_api.async_playwright") as mock_p:
        mock_browser = AsyncMock()
        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_browser.contexts = [mock_context]
        mock_p.return_value.__aenter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("line_utils.get_line_page", return_value=mock_page), \
             patch("line_utils.is_logged_in", return_value=True), \
             patch("line_utils.open_chat", return_value=mock_res):
            
            import mcp_server
            result = await mcp_server.open_chat(chat_name="Junyu", chat_type="private", chat_id="u123", port=9222)
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["chat_name"] == "Junyu"

@pytest.mark.asyncio
async def test_send_line_message_tool():
    mock_page = AsyncMock()
    
    with patch("playwright.async_api.async_playwright") as mock_p:
        mock_browser = AsyncMock()
        mock_context = MagicMock()
        mock_browser.contexts = [mock_context]
        mock_p.return_value.__aenter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("line_utils.get_line_page", return_value=mock_page), \
             patch("line_utils.select_chat", return_value={"status": "success"}), \
             patch("line_utils.send_message", return_value=AsyncMock()):
            
            import mcp_server
            result = await mcp_server.send_line_message(chat_name="test_chat", text="hello")
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["chat"] == "test_chat"
            assert data["text"] == "hello"

@pytest.mark.asyncio
async def test_get_line_messages_tool():
    mock_page = AsyncMock()
    mock_msgs = [
        {"text": "msg1", "sender": "Wayne", "timestamp": "10:00"},
        {"text": "msg2", "sender": "俊羽", "timestamp": "10:01"}
    ]
    
    with patch("playwright.async_api.async_playwright") as mock_p:
        mock_browser = AsyncMock()
        mock_context = MagicMock()
        mock_browser.contexts = [mock_context]
        mock_p.return_value.__aenter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
        
        with patch("line_utils.get_line_page", return_value=mock_page), \
             patch("line_utils.select_chat", return_value={"status": "success"}), \
             patch("line_utils.extract_messages", return_value=mock_msgs):
            
            import mcp_server
            result = await mcp_server.get_line_messages(chat_name="test_chat", limit=1)
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["count"] == 1
            assert data["messages"][0]["text"] == "msg2"
            assert data["messages"][0]["sender"] == "俊羽"

@pytest.mark.asyncio
async def test_run_task_tool():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "task completed successfully"
        mock_run.return_value.stderr = ""
        os.environ["GEMINI_API_KEY"] = "fake_key"

        import mcp_server
        result = await mcp_server.run_task(chat_name="test_chat", task="test_task")
        data = json.loads(result)

        assert data["status"] == "completed"
        assert "task completed successfully" in data["stdout"]
        assert mock_run.called
