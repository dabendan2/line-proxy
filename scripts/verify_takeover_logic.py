import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# 模擬 Playwright 與 AI 模組
sys.modules['playwright'] = MagicMock()
sys.modules['playwright.async_api'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

# 此處假設 engine.py 已存在於路徑中
from engine import LineProxyEngine

@pytest.fixture
def engine():
    with patch('google.generativeai.configure'), \
         patch('google.generativeai.GenerativeModel'):
        return LineProxyEngine(page=AsyncMock(), chat_name="test", task="Task", api_key="key")

@pytest.mark.asyncio
async def test_takeover_logic_silence_on_self(engine):
    """驗證：若最後一則是己方發言，接管時應保持靜默。"""
    msgs = [{"text": "AI: Hello", "time": "12:00", "is_self_dom": True}]
    engine.rebuild_memory(msgs)
    assert engine.state["startup_action_needed"] is False

@pytest.mark.asyncio
async def test_takeover_logic_respond_on_other(engine):
    """驗證：若最後一則是對方發言，接管時應觸發回覆。"""
    msgs = [{"text": "User: Hi", "time": "12:00", "is_self_dom": False}]
    engine.rebuild_memory(msgs)
    assert engine.state["startup_action_needed"] is True
