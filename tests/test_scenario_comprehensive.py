import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import time

# Ensure src is in path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(base_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Create consistent mocks
mock_extract = AsyncMock()
mock_send = AsyncMock()

# Patch sys.modules for LineProxyEngine imports
with patch.dict('sys.modules', {
    'playwright': MagicMock(),
    'playwright.async_api': MagicMock(),
    'google.genai': MagicMock(),
    'line_utils': MagicMock(
        extract_messages=mock_extract,
        send_message=mock_send,
        HERMES_PREFIX="[Hermes]"
    )
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
    mock_extract.reset_mock()
    mock_send.reset_mock()
    
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="Mock etiquette")))))), \
         patch('engine.genai.Client', return_value=mock_genai_client_inst):
        yield {
            "client": mock_genai_client_inst,
            "send": mock_send,
            "extract": mock_extract
        }

@pytest.mark.asyncio
async def test_silent_accomplishment_after_acknowledgment(mock_page, engine_mocks):
    """
    場景測試：驗證當任務已完成且對方回覆「好的」時，Hermes 是否會保持靜默並直接輸出 [END] 標籤。
    """
    client = engine_mocks["client"]
    mock_send = engine_mocks["send"]
    mock_extract = engine_mocks["extract"]

    # 任務：訂位 5/11 13:00
    task = "我想預約 5/11 13:00 2位。"

    # 模擬歷史：Hermes 提供資訊後，店員說「好的」
    msgs = [
        {"text": "好的，了解了。", "is_self_dom": False},
        {"text": "您好，我是 俊羽 的AI代理 Hermes。想預約 5/11 13:00...", "is_self_dom": True}
    ]
    mock_extract.return_value = msgs

    # 設定模擬模型回覆：僅包含標籤，不包含社交回覆
    class MockResponse:
        def __init__(self, text): self.text = text
    client.models.generate_content.return_value = MockResponse('[END, reason="accomplished", report="店員已確認預約，任務圓滿完成"]')

    proxy = LineProxyEngine(page=mock_page, chat_name="test_silent", task=task, api_key="fake")
    proxy.state = {
        "sent_messages": ["您好，我是 俊羽 的AI代理 Hermes。想預約 5/11 13:00..."],
        "last_processed_msg": "好的，了解了。",
        "exit_at": None, "final_report": None
    }

    await proxy.generate_and_send_reply(msgs)

    # 驗證 1：send_message 不應該被呼叫（靜默退場）
    mock_send.assert_not_called()
    
    # 驗證 2：系統正確設定 accomplished 狀態與報告
    assert proxy.state["final_report"] == "店員已確認預約，任務圓滿完成"
    assert proxy.state["exit_at"] > time.time()

@pytest.mark.asyncio
async def test_focused_reply_to_redundant_staff_question(mock_page, engine_mocks):
    """
    驗證聚焦回答邏輯。
    """
    client = engine_mocks["client"]
    mock_send = engine_mocks["send"]
    mock_extract = engine_mocks["extract"]

    task = "我想預約 5/11 13:00 2位。請註明會有 2 位小朋友隨行。"
    msgs = [
        {"text": "了解，那請問當天總共會有幾位小朋友呢？", "is_self_dom": False},
        {"text": "您好...我想預約 5/11 13:00 的 2 位位置，當天會有 2 位小朋友隨行。", "is_self_dom": True}
    ]
    mock_extract.return_value = msgs

    class MockResponse:
        def __init__(self, text): self.text = text
    client.models.generate_content.return_value = MockResponse("總共會有 2 位小朋友喔，謝謝！")

    proxy = LineProxyEngine(page=mock_page, chat_name="test_focused", task=task, api_key="fake")
    proxy.state = {
        "sent_messages": ["您好... 2 位小朋友隨行。"],
        "last_processed_msg": "了解，那請問當天總共會有幾位小朋友呢？",
        "exit_at": None, "final_report": None
    }

    await proxy.generate_and_send_reply(msgs)
    mock_send.assert_called_once()
    sent_text = str(mock_send.call_args[0][1])
    assert "2 位小朋友" in sent_text
    assert "Hermes" not in sent_text
