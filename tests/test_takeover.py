import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
import sys

# Mocking modules before import
sys.modules['playwright'] = MagicMock()
sys.modules['playwright.async_api'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

from engine import LineProxyEngine

@pytest.fixture
def mock_page():
    page = AsyncMock()
    return page

@pytest.fixture
def engine(mock_page):
    with patch('google.generativeai.configure'), \
         patch('google.generativeai.GenerativeModel'):
        engine = LineProxyEngine(
            page=mock_page,
            chat_name="test_chat",
            task="一般任務",
            api_key="fake_key"
        )
        return engine

@pytest.mark.asyncio
async def test_takeover_hermes_spoke_last_silence(engine, mock_page):
    """如果是己方最後發言，接管時不應該再發。"""
    # Arrange: 模擬對話，最後一則是 Hermes 發送的
    msgs = [
        {"text": "Hermes: 請問還有位子嗎？", "time": "12:00 PM", "is_self_dom": True},
        {"text": "User: 你好", "time": "11:55 AM", "is_self_dom": False}
    ]
    
    # 執行記憶重建
    engine.state = engine.history.rebuild_state(msgs, engine.task_description)
    assert engine.state["startup_action_needed"] is False
    
    # 模擬 run() 中的啟動邏輯
    with patch('line_utils.extract_messages', return_value=msgs):
        with patch.object(engine, 'generate_and_send_reply', new_callable=AsyncMock) as mock_reply:
            if engine.state.get("startup_action_needed") or "啟動" in engine.task_description:
                if msgs[0]["text"].strip() not in engine.state["sent_messages"]:
                    await engine.generate_and_send_reply(msgs)
            
            mock_reply.assert_not_called()

@pytest.mark.asyncio
async def test_takeover_user_spoke_last_respond(engine, mock_page):
    """如果是對方最後發言，接管時應該立即回覆。"""
    msgs = [
        {"text": "User: 13:00 有位子喔", "time": "12:05 PM", "is_self_dom": False},
        {"text": "Hermes: 請問還有位子嗎？", "time": "12:00 PM", "is_self_dom": True}
    ]
    
    engine.state = engine.history.rebuild_state(msgs, engine.task_description)
    assert engine.state["startup_action_needed"] is True
    
    with patch('line_utils.extract_messages', return_value=msgs):
        with patch.object(engine, 'generate_and_send_reply', new_callable=AsyncMock) as mock_reply:
            if engine.state.get("startup_action_needed"):
                if msgs[0]["text"].strip() not in engine.state["sent_messages"]:
                    await engine.generate_and_send_reply(msgs)
            
            mock_reply.assert_called_once()
