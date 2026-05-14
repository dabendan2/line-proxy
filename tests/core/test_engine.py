import pytest
import asyncio
import time
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from core.engine import ChatEngine

@pytest.mark.asyncio
async def test_engine_runtime_timeout_logging():
    """
    Verify that when RUNTIME_TIMEOUT is reached, 
    the error is logged to history_manager and returned.
    """
    mock_channel = AsyncMock()
    mock_channel.select_chat.return_value = {"status": "success"}
    mock_channel.extract_messages.return_value = [{"text": "m", "sender": "Chat"}]
    
    with patch("core.history.HistoryManager.write_log") as mock_log, \
         patch("google.genai.Client"), \
         patch("core.engine.POLL_INTERVAL", 0.01), \
         patch("core.engine.RUNTIME_TIMEOUT", 0.1): 
        
        engine = ChatEngine(mock_channel, "test_chat", "test_task", api_key="test_key")
        engine.generate_and_send_reply = AsyncMock()
        
        report = await engine.run()
        
        # 1. Check if report is returned correctly
        assert report == "[RESTART_REQUIRED] Runtime limit reached."
        
        # 2. Check if it was logged
        log_calls = [call[0][0] for call in mock_log.call_args_list]
        assert any("[RESTART_REQUIRED]" in str(msg) for msg in log_calls)
        assert any("Session concluded." in str(msg) for msg in log_calls)

@pytest.mark.asyncio
async def test_run_engine_cli_reports_timeout(capsys):
    """
    Verify that run_engine.py reports the real status 
    instead of hardcoded success on timeout.
    """
    from channels.line.run_engine import main
    
    with patch("channels.line.run_engine.ChatEngine") as mock_engine_class, \
         patch("channels.line.run_engine.PIDLock"), \
         patch("os.environ", {"GOOGLE_API_KEY": "test"}), \
         patch("channels.line.run_engine.TaskRefactorer", create=True), \
         patch("channels.line.run_engine.async_playwright"), \
         patch("channels.line.run_engine.line_utils.get_line_page"), \
         patch("sys.argv", ["run_engine.py", "--chat_name", "test", "--task", "test"]):
        
        mock_instance = mock_engine_class.return_value
        mock_instance.run = AsyncMock(return_value="[RESTART_REQUIRED] Runtime limit reached.")
        
        with pytest.raises(SystemExit) as excinfo:
            await main()
        
        assert excinfo.value.code == 1
            
    captured = capsys.readouterr()
    assert "ERROR" in captured.out
    assert "[RESTART_REQUIRED]" in captured.out
