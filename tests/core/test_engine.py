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
        assert report == "[SILENT_RESTART_NEEDED] Runtime limit reached."
        
        # 2. Check if it was logged
        log_calls = [call[0][0] for call in mock_log.call_args_list]
        assert any("[SILENT_RESTART_NEEDED]" in str(msg) for msg in log_calls)
        assert any("Session concluded." in str(msg) for msg in log_calls)

@pytest.mark.asyncio
async def test_run_engine_cli_reports_timeout(capsys):
    """
    Verify that run_engine.py reports the real status
    instead of hardcoded success on timeout.
    """
    from core.run_engine import main
    
    with patch("core.run_engine.ChatEngine") as mock_engine_class, \
         patch("core.run_engine.PIDLock"), \
         patch("os.environ", {"GOOGLE_API_KEY": "test"}), \
         patch("core.refactorer.TaskRefactorer") as mock_refactorer_class, \
         patch("core.run_engine.async_playwright") as mock_p, \
         patch("core.run_engine.ChannelFactory") as mock_factory, \
         patch("sys.argv", ["run_engine.py", "--chat_name", "test", "--task", "test"]):
        
        mock_refactorer_class.return_value.refactor.return_value = "test"
        mock_factory.create_instance.return_value = MagicMock()
        
        # Mock line_utils for the page retrieval logic
        mock_line_utils = MagicMock()
        mock_line_utils.get_line_page = AsyncMock(return_value=MagicMock())
        with patch.dict("sys.modules", {"channels.line": MagicMock(driver=mock_line_utils)}):
            mock_instance = mock_engine_class.return_value
            mock_instance.run = AsyncMock(return_value="[SILENT_RESTART_NEEDED] Runtime limit reached.")
            
            with pytest.raises(SystemExit) as excinfo:
                await main()
            
            assert excinfo.value.code == 1
            
    captured = capsys.readouterr()
    assert "ERROR" in captured.out
    assert "[SILENT_RESTART_NEEDED]" in captured.out

@pytest.mark.asyncio
async def test_check_spamming_visibility():
    """
    Verify that technical messages starting with [系統] or [TOOL] 
    do NOT count towards the spamming quota.
    """
    mock_channel = AsyncMock()
    engine = ChatEngine(mock_channel, "test_chat", "test_task", api_key="test_key")
    
    # Cases that SHOULD NOT trigger spamming (limit is 3)
    msgs_ok = [
        {"sender": "Hermes", "text": "Msg 1"},
        {"sender": "Hermes", "text": "[系統] 工具執行中..."},
        {"sender": "Hermes", "text": "[TOOL] Query results..."},
        {"sender": "Hermes", "text": "Msg 2"},
        # Total visible Hermes messages: 2
    ]
    # Should not raise
    engine._check_spamming(msgs_ok)

    # Case that SHOULD trigger spamming
    msgs_bad = [
        {"sender": "Hermes", "text": "Msg 1"},
        {"sender": "Hermes", "text": "[系統] Hidden"},
        {"sender": "Hermes", "text": "Msg 2"},
        {"sender": "Hermes", "text": "[TOOL] Hidden"},
        {"sender": "Hermes", "text": "Msg 3"},
        # Total visible Hermes messages: 3 -> Should raise
    ]
    with pytest.raises(Exception) as excinfo:
        engine._check_spamming(msgs_bad)
    assert "SECURITY_PROTOCOL_ACTIVATED" in str(excinfo.value)
    assert "(3)" in str(excinfo.value)
