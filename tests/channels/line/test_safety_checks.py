import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.abspath("src"))
from channels.line import driver as line_driver
from utils.config import HERMES_PREFIX

@pytest.mark.asyncio
async def test_send_message_blocks_unauthorized_stack():
    """
    Verify that send_message raises PermissionError when not called from run_task or ChatEngine.
    """
    mock_page = MagicMock()
    
    with pytest.raises(PermissionError, match="Access Denied"):
        # Calling directly from a test function (unauthorized stack)
        await line_driver.send_message(mock_page, "Should fail")

@pytest.mark.asyncio
async def test_send_message_forces_hermes_prefix():
    """
    Verify that send_message automatically prepends the HERMES_PREFIX if missing.
    We mock 'inspect.stack' to simulate a valid caller.
    """
    mock_page = MagicMock()
    mock_page.locator().first.click = AsyncMock()
    mock_page.keyboard.type = AsyncMock()
    mock_page.keyboard.press = AsyncMock()
    
    # Mock stack to include 'run_task'
    mock_stack = [MagicMock(function="run_task")]
    
    with patch("inspect.stack", return_value=mock_stack):
        await line_driver.send_message(mock_page, "Hello world")
        
        # Check if the prefix was added
        # page.keyboard.type is called with the prefixed text
        # Since we use page.keyboard.type(text), let's check its calls
        sent_text = mock_page.keyboard.type.call_args[0][0]
        assert sent_text.startswith(HERMES_PREFIX)
        assert "Hello world" in sent_text

@pytest.mark.asyncio
async def test_send_image_blocks_unauthorized_stack():
    """
    Verify that send_image raises PermissionError when not called from authorized functions.
    """
    mock_page = MagicMock()
    
    with pytest.raises(PermissionError, match="Access Denied"):
        await line_driver.send_image(mock_page, "/path/to/img.png")
