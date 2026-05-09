
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
    engine.rebuild_memory(msgs)
    assert engine.state["startup_action_needed"] is False
    
    # 模擬 run() 中的啟動邏輯
    with patch('line_utils.extract_messages', return_value=msgs):
        with patch.object(engine, 'generate_and_send_reply', new_callable=AsyncMock) as mock_reply:
            # 模擬啟動檢查邏輯
            if engine.state.get("startup_action_needed") or "啟動" in engine.task_description:
                if msgs[0]["text"].strip() not in engine.state["sent_messages"]:
                    await engine.generate_and_send_reply(msgs)
            
            # Assert: 不應該呼叫發送函數
            mock_reply.assert_not_called()

@pytest.mark.asyncio
async def test_takeover_user_spoke_last_respond(engine, mock_page):
    """如果是對方最後發言，接管時應該立即回覆。"""
    # Arrange: 模擬對話，最後一則是 User 發送的
    msgs = [
        {"text": "User: 13:00 有位子喔", "time": "12:05 PM", "is_self_dom": False},
        {"text": "Hermes: 請問還有位子嗎？", "time": "12:00 PM", "is_self_dom": True}
    ]
    
    # 執行記憶重建
    engine.rebuild_memory(msgs)
    assert engine.state["startup_action_needed"] is True
    
    # 模擬 run() 中的啟動邏輯
    with patch('line_utils.extract_messages', return_value=msgs):
        with patch.object(engine, 'generate_and_send_reply', new_callable=AsyncMock) as mock_reply:
            if engine.state.get("startup_action_needed") or "啟動" in engine.task_description:
                if msgs[0]["text"].strip() not in engine.state["sent_messages"]:
                    await engine.generate_and_send_reply(msgs)
            
            # Assert: 應該呼叫發送函數
            mock_reply.assert_called_once()

@pytest.mark.asyncio
async def test_start_task_force_action_on_new_chat(engine, mock_page):
    """若是『啟動』類任務且尚未有任何發言，應強制發起對話。"""
    engine.task_description = "啟動遊戲"
    # 假設這是一個全新的對話，最後一則是人類很久以前的無關訊息
    msgs = [{"text": "無關訊息", "time": "Yesterday", "is_self_dom": False}]
    
    engine.rebuild_memory(msgs)
    
    with patch('line_utils.extract_messages', return_value=msgs):
        with patch.object(engine, 'generate_and_send_reply', new_callable=AsyncMock) as mock_reply:
            if engine.state.get("startup_action_needed") or "啟動" in engine.task_description:
                if msgs[0]["text"].strip() not in engine.state["sent_messages"]:
                    await engine.generate_and_send_reply(msgs)
            
            mock_reply.assert_called_once()

@pytest.mark.asyncio
async def test_takeover_from_dom_only_memory(engine, mock_page):
    """即便 Log 遺失，只要 DOM 顯示最後是己方發言，也不應重發。"""
    # Arrange: 清空 Log，僅靠 DOM 識別
    engine.log_path = "/tmp/non_existent.log"
    msgs = [
        {"text": "己方發言(僅DOM)", "time": "12:00 PM", "is_self_dom": True}
    ]
    
    # Act
    engine.rebuild_memory(msgs)
    
    # Assert
    assert "己方發言(僅DOM)" in engine.state["sent_messages"]
    assert engine.state["startup_action_needed"] is False
    
    with patch('line_utils.extract_messages', return_value=msgs):
        with patch.object(engine, 'generate_and_send_reply', new_callable=AsyncMock) as mock_reply:
            if engine.state.get("startup_action_needed") or "啟動" in engine.task_description:
                if msgs[0]["text"].strip() not in engine.state["sent_messages"]:
                    await engine.generate_and_send_reply(msgs)
            mock_reply.assert_not_called()
