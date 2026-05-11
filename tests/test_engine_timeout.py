import pytest
import asyncio
import time
import os
import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from engine import LineProxyEngine

@pytest.mark.asyncio
async def test_engine_runtime_timeout():
    # Mock dependencies
    mock_page = MagicMock()
    async def _async_mock(): return None
    mock_page.bring_to_front = _async_mock
    
    # Mock line_utils functions
    with patch("line_utils.select_chat", return_value={"status": "success"}), \
         patch("line_utils.extract_messages", return_value=[{"text": "msg1", "is_self_dom": False}]), \
         patch("line_utils.send_message", return_value=None), \
         patch("history_manager.HistoryManager.rebuild_state", return_value={}), \
         patch("history_manager.HistoryManager.get_full_context", return_value=[]), \
         patch("history_manager.HistoryManager.write_log"), \
         patch("google.genai.Client"), \
         patch("engine.POLL_INTERVAL", 0.1), \
         patch("engine.RUNTIME_TIMEOUT", 1): # Set timeout to 1 second for testing
        
        engine = LineProxyEngine(mock_page, "test_chat", "test_task", api_key="test_key")
        
        # Mock generate_and_send_reply to do nothing
        async def _mock_reply(msgs): pass
        engine.generate_and_send_reply = _mock_reply
        
        start = time.time()
        await engine.run()
        end = time.time()
        
        # Verify it exited around 1 second
        assert 1 <= (end - start) < 3
        assert "[RESTART_REQUIRED]" in engine.state["final_report"]
        print(f"\nTest passed: Engine timed out gracefully in {end-start:.2f}s")

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
