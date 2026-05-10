import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import time
import asyncio

# Ensure src is in path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(base_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Define robust mocks for the modules
mock_extract = AsyncMock()
mock_send = AsyncMock()
mock_genai_client_inst = MagicMock()
mock_genai_client_class = MagicMock(return_value=mock_genai_client_inst)

# Patch sys.modules BEFORE importing anything from src
with patch.dict('sys.modules', {
    'playwright': MagicMock(),
    'playwright.async_api': MagicMock(),
    'google.genai': MagicMock(Client=mock_genai_client_class),
    'line_utils': MagicMock(
        extract_messages=mock_extract,
        send_message=mock_send,
        HERMES_PREFIX="[Hermes]"
    )
}):
    import engine
    from engine import LineProxyEngine
    from history_manager import HistoryManager

@pytest.fixture
def mock_page():
    p = MagicMock()
    p.bring_to_front = AsyncMock()
    return p

@pytest.fixture
def engine_env():
    # Reset all mocks
    mock_extract.reset_mock()
    mock_send.reset_mock()
    mock_genai_client_inst.models.generate_content.reset_mock()
    
    # Mock open for etiquette.md
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="Mock etiquette")))))):
        yield {
            "client": mock_genai_client_inst,
            "send": mock_send,
            "extract": mock_extract
        }

class MockResponse:
    def __init__(self, text):
        self.text = text

@pytest.mark.asyncio
async def test_reason_consulting_mapping(mock_page, engine_env):
    client = engine_env["client"]
    client.models.generate_content.return_value = MockResponse('問問俊羽。[END, reason="consulting", report="詢問電話"]')
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    now = time.time()
    await proxy.generate_and_send_reply([{"text": "電話？", "is_self_dom": False}])
    
    assert proxy.state["exit_at"] is not None
    assert 110 < (proxy.state["exit_at"] - now) < 130
    assert proxy.state["final_report"] == "詢問電話"

@pytest.mark.asyncio
async def test_no_redundant_intro_logic(mock_page, engine_env):
    client = engine_env["client"]
    mock_send = engine_env["send"]
    
    # History already has Hermes
    msgs = [{"text": "哈囉", "is_self_dom": False}, {"text": "我是 Hermes", "is_self_dom": True}]
    
    client.models.generate_content.return_value = MockResponse("這部分沒問題。")
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    proxy.state["sent_messages"] = ["我是 Hermes"]
    
    await proxy.generate_and_send_reply(msgs)
    
    mock_send.assert_called_once()
    sent_text = str(mock_send.call_args[0][1])
    assert "Hermes" not in sent_text

@pytest.mark.asyncio
async def test_silent_completion_on_acknowledgment(mock_page, engine_env):
    client = engine_env["client"]
    mock_send = engine_env["send"]
    
    # User says "OK"
    msgs = [{"text": "好的，了解了。", "is_self_dom": False}]
    client.models.generate_content.return_value = MockResponse('[END, reason="accomplished", report="完成"]')
    
    proxy = LineProxyEngine(page=mock_page, chat_name="test", task="訂位", api_key="fake")
    await proxy.generate_and_send_reply(msgs)
    
    mock_send.assert_not_called()
    assert proxy.state["final_report"] == "完成"

def test_restart_safety_logic():
    """驗證 rebuild_state 是否能防止重啟後重複發言。"""
    mgr = HistoryManager(chat_name="test")
    # 最後一則是 Hermes 發出的
    msgs = [
        {"text": "請問 5/11 有位子嗎？", "is_self_dom": True, "has_hermes_prefix": True},
        {"text": "您好", "is_self_dom": False}
    ]
    state = mgr.rebuild_state(msgs, "訂位")
    assert state["startup_action_needed"] is False
    assert state["last_processed_msg"] == "請問 5/11 有位子嗎？"

def test_history_boundary_logic():
    """驗證 get_full_context 是否能排除已忽略訊息。"""
    mgr = HistoryManager(chat_name="test", last_ignored_msg="忽略", last_ignored_time="10:00")
    msgs = [
        {"text": "新訊息", "is_self_dom": False},
        {"text": "忽略", "is_self_dom": False},
        {"text": "老訊息", "is_self_dom": False}
    ]
    context = mgr.get_full_context(msgs, [])
    assert len(context) == 1
    assert "User/Staff: 新訊息" in context[0]
