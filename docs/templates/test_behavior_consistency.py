import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import time

# Ensure src is in path
# Assumes structure: /src/engine.py, /tests/this_file.py
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(base_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Mock external modules for import safety
mock_line_utils = MagicMock()
mock_line_utils.extract_messages = AsyncMock()
mock_line_utils.send_message = AsyncMock()
mock_line_utils.HERMES_PREFIX = "[Hermes]"

with patch.dict('sys.modules', {
    'playwright': MagicMock(),
    'playwright.async_api': MagicMock(),
    'google.genai': MagicMock(),
    'line_utils': mock_line_utils
}):
    from engine import LineProxyEngine

@pytest.fixture
def mock_page():
    p = MagicMock()
    p.bring_to_front = AsyncMock()
    return p

@pytest.fixture
def engine_mocks():
    mock_genai_client_inst = MagicMock()
    # Reset mocks
    mock_line_utils.extract_messages.reset_mock()
    mock_line_utils.send_message.reset_mock()
    mock_genai_client_inst.models.generate_content.reset_mock()
    
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="Mock etiquette")))))), \
         patch('engine.genai.Client', return_value=mock_genai_client_inst):
        yield {
            "client": mock_genai_client_inst,
            "send": mock_line_utils.send_message,
            "extract": mock_line_utils.extract_messages
        }

@pytest.mark.asyncio
async def test_no_redundant_intro(mock_page, engine_mocks):
    """Verify Hermes doesn't re-introduce if history already shows an intro."""
    client = engine_mocks["client"]
    mock_send = engine_mocks["send"]
    mock_extract = engine_mocks["extract"]

    msgs = [
        {"text": "Any seats?", "is_self_dom": False},
        {"text": "Hello, I am Hermes. I want to book...", "is_self_dom": True, "has_hermes_prefix": True}
    ]
    mock_extract.return_value = msgs

    mock_resp = MagicMock()
    mock_resp.text = "Yes, there are seats."
    client.models.generate_content.return_value = mock_resp

    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="book", api_key="fake")
    proxy.state = {
        "sent_messages": ["Hello, I am Hermes. I want to book..."],
        "last_processed_msg": "Any seats?",
    }

    await proxy.generate_and_send_reply(msgs)
    mock_send.assert_called_once()
    sent_text = str(mock_send.call_args[0][1])
    assert "Hermes" not in sent_text # No redundant intro

@pytest.mark.asyncio
async def test_consulting_on_missing_info(mock_page, engine_mocks):
    """Verify 'consulting' tag is triggered when staff asks for unprovided info."""
    client = engine_mocks["client"]
    mock_send = engine_mocks["send"]
    
    mock_resp = MagicMock()
    mock_resp.text = 'I need to check with Chunyu. [END, reason="consulting", report="Staff asked for seat type"]'
    client.models.generate_content.return_value = mock_resp

    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="book 5/11", api_key="fake")
    await proxy.generate_and_send_reply([{"text": "Indoor or outdoor?", "is_self_dom": False}])

    assert proxy.state["final_report"] == "Staff asked for seat type"
    assert proxy.state["exit_at"] > time.time()

@pytest.mark.asyncio
async def test_goodbye_restart_safety(mock_page, engine_mocks):
    """Verify silence if conversation already ended in history."""
    client = engine_mocks["client"]
    mock_send = engine_mocks["send"]
    
    mock_resp = MagicMock()
    mock_resp.text = '[END, reason="goodbye", report="Ended"]'
    client.models.generate_content.return_value = mock_resp

    msgs = [
        {"text": "Bye!", "is_self_dom": False},
        {"text": "Goodbye, have a nice day!", "is_self_dom": True}
    ]
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="book", api_key="fake")
    proxy.state = {"sent_messages": ["Goodbye!"], "last_processed_msg": "___RESTART___"}

    await proxy.generate_and_send_reply(msgs)
    mock_send.assert_not_called()
