import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Ensure the src directory is in the path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import line_utils

@pytest.mark.asyncio
async def test_extract_messages_fails_when_container_missing():
    """
    TDD: Verify that extract_messages raises an exception when the chatroom container is missing.
    This prevents silent failures where an empty list is returned instead of an error.
    """
    mock_page = MagicMock()
    # Mocking the first evaluate call (scroll)
    mock_page.evaluate = AsyncMock()
    # Mocking the second evaluate call (extraction) to raise error
    mock_page.evaluate.side_effect = [None, Exception("JS Error: Error: Chatroom container not found")]
    
    with pytest.raises(Exception) as excinfo:
        await line_utils.extract_messages(mock_page, "Owner", "Chat")
    
    assert "Chatroom container not found" in str(excinfo.value)

@pytest.mark.asyncio
async def test_extract_messages_returns_empty_list_when_no_messages():
    """
    Verify that extract_messages returns an empty list when the container exists but has no message items.
    """
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    # First call: scroll (None), Second call: extraction ([])
    mock_page.evaluate.side_effect = [None, []]
    
    result = await line_utils.extract_messages(mock_page, "Owner", "Chat")
    
    assert isinstance(result, list)
    assert len(result) == 0

@pytest.mark.asyncio
async def test_extract_messages_success_with_data():
    """
    Verify that extract_messages correctly returns structured message data.
    """
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock()
    
    mock_data = [
        {"sender": "Wayne", "text": "Hello", "timestamp": "10:00"},
        {"sender": "Hermes", "text": "Hi there", "timestamp": "10:01"}
    ]
    
    # First call: scroll (None), Second call: extraction
    mock_page.evaluate.side_effect = [None, mock_data]
    
    result = await line_utils.extract_messages(mock_page, "Owner", "Chat")
    
    assert len(result) == 2
    assert result[0]["sender"] == "Wayne"
    assert result[1]["text"] == "Hi there"
