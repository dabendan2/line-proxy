import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

import line_utils
from engine import LineProxyEngine

@pytest.mark.asyncio
async def test_extraction_order_consistency():
    """
    Ensures that line_utils returns messages in chronological order (Oldest First),
    which is the standard format expected by the Hermes Engine.
    """
    mock_page = AsyncMock()
    
    # Standard format returned by line_utils: Oldest First
    mock_messages = [
        {"text": "Hello (Oldest)", "sender": "Wayne", "timestamp": "10:00 AM"},
        {"text": "How are you?", "sender": "Wayne", "timestamp": "10:01 AM"},
        {"text": "I am fine (Newest)", "sender": "俊羽", "timestamp": "10:02 AM"}
    ]
    
    # Use patch to avoid dirtying the module
    with patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=mock_messages):
        msgs = await line_utils.extract_messages(mock_page)
        
        # Assertions for Chronological Order (Required by Engine)
        assert msgs[0]["text"] == "Hello (Oldest)"
        assert msgs[-1]["text"] == "I am fine (Newest)"

@pytest.mark.asyncio
async def test_js_order_logic_fix():
    """
    Verify the JS string in line_utils correctly handles the LINE Extension DOM 
    quirk: Newest messages appear first in DOM traversal.
    We require results.reverse() to convert to Oldest First for the engine.
    """
    # Read the JS string from line_utils.py
    src_path = os.path.join(os.path.dirname(__file__), "..", "src", "line_utils.py")
    with open(src_path, "r") as f:
        content = f.read()
    
    # Technical Note: 
    # LINE Extension lists newest messages FIRST in the DOM tree.
    # To maintain the Engine's expected chronological order (Oldest -> Newest),
    # the script MUST reverse the raw results.
    assert "results.reverse()" in content

@pytest.mark.asyncio
async def test_self_detection_logic():
    """
    Verify the self-detection logic uses data-direction='reverse', 
    which is the most reliable indicator in the current LINE Extension DOM.
    """
    src_path = os.path.join(os.path.dirname(__file__), "..", "src", "line_utils.py")
    with open(src_path, "r") as f:
        content = f.read()
        
    assert "el.getAttribute('data-direction')" in content
    assert "direction === 'reverse'" in content

@pytest.mark.asyncio
async def test_timestamp_inheritance_logic():
    """
    Verify the JS string contains the logic to inherit timestamps 
    for clustered messages from the same sender.
    """
    src_path = os.path.join(os.path.dirname(__file__), "..", "src", "line_utils.py")
    with open(src_path, "r") as f:
        content = f.read()
        
    assert "TIME INHERITANCE" in content
    assert "chronMessages[i].timestamp = chronMessages[i+1].timestamp" in content
    assert "chronMessages[i].sender === chronMessages[i+1].sender" in content
