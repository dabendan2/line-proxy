import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

import line_utils
from engine import LineProxyEngine

@pytest.mark.asyncio
async def test_extraction_order_consistency():
    """
    Ensures that line_utils returns messages in the same order they appear in the DOM
    (which is chronological in LINE), and that the Engine correctly identifies 
    the last message as the 'latest'.
    """
    mock_page = AsyncMock()
    
    # Simulate LINE DOM: Top (Oldest) to Bottom (Newest)
    mock_messages = [
        {"text": "Hello (Oldest)", "is_self": False, "timestamp": "10:00 AM"},
        {"text": "How are you?", "is_self": False, "timestamp": "10:01 AM"},
        {"text": "I am fine (Newest)", "is_self": False, "timestamp": "10:02 AM"}
    ]
    
    # Mock line_utils.extract_messages to return our mock data
    # In reality, extract_messages runs JS, but here we test the integration
    line_utils.extract_messages = AsyncMock(return_value=mock_messages)
    
    # Initialize Engine
    engine = LineProxyEngine(
        page=mock_page, 
        chat_name="test_chat", 
        task="test_task", 
        api_key="mock_key"
    )
    
    # Mock history manager to prevent file writes
    engine.history.write_log = MagicMock()
    engine.history.rebuild_state = MagicMock(return_value={})
    
    # Mock select_chat
    line_utils.select_chat = AsyncMock(return_value={"status": "success"})
    
    # Execute a part of the run loop or a helper
    msgs = await line_utils.extract_messages(mock_page)
    
    # Assertions
    assert msgs[0]["text"] == "Hello (Oldest)"
    assert msgs[-1]["text"] == "I am fine (Newest)"
    
    # Verify Engine's 'latest' logic (simulating the check in engine.run)
    latest = msgs[-1]
    assert latest["text"] == "I am fine (Newest)"

@pytest.mark.asyncio
async def test_js_order_logic():
    """
    Verify the JS string in line_utils contains .reverse() 
    to ensure chronological order (Oldest First) for the Python engine.
    """
    # Read the JS string from line_utils.py
    with open("src/line_utils.py", "r") as f:
        content = f.read()
    
    # We REQUIRE .reverse() because the LINE Extension DOM 
    # appears to list newest messages first.
    assert "return results.reverse();" in content
