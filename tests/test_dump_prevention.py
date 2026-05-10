import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# Mocks
mock_extract = AsyncMock()
mock_send = AsyncMock()
mock_genai_client_inst = MagicMock()
mock_genai_client_class = MagicMock(return_value=mock_genai_client_inst)

# Standard mock for prompt verification
def get_mock_response(text):
    m = MagicMock()
    m.text = text
    return m

with patch.dict('sys.modules', {
    'playwright': MagicMock(),
    'playwright.async_api': MagicMock(),
    'google.genai': MagicMock(Client=mock_genai_client_class),
    'line_utils': MagicMock(
        extract_messages=mock_extract,
        send_message=mock_send,
        HERMES_PREFIX="[Hermes]",
        select_chat=AsyncMock(return_value={"status": "success"})
    )
}):
    from engine import LineProxyEngine

@pytest.fixture(autouse=True)
def reset_all_mocks():
    mock_extract.reset_mock()
    mock_send.reset_mock()
    mock_genai_client_inst.models.generate_content.reset_mock()

@pytest.mark.asyncio
async def test_incremental_disclosure_enforcement():
    """
    驗證代理人在面對複雜任務時，是否會嚴格執行「循序漸進」原則。
    """
    complex_task = (
        "預訂5/11 13:00 2大2小 要求1個兒童餐具 及保留停車位。"
        "訂位資訊 賴俊羽 0958078550"
    )
    
    # 模擬 LLM 遵守規則：僅詢問時段
    mock_genai_client_inst.models.generate_content.return_value = get_mock_response(
        "您好，我是 俊羽 的 AI 代理。想預訂 5/11 13:00 還有位置嗎？ [WAIT_FOR_USER_INPUT]"
    )
    
    mock_page = MagicMock()
    proxy = LineProxyEngine(page=mock_page, chat_name="娜比", task=complex_task, api_key="fake")
    
    await proxy.generate_and_send_reply([]) 
    
    mock_send.assert_called_once()
    sent_text = mock_send.call_args[0][1]
    
    # 驗證內容是否簡短且不包含後續階段資訊
    assert "0958078550" not in sent_text
    assert "兒童餐具" not in sent_text
    assert len(sent_text) <= 40 # 確保遵守字數限制
    
    # 驗證 Prompt 是否包含硬性約束
    actual_prompt = mock_genai_client_inst.models.generate_content.call_args[1]['contents']
    assert "禁止一次性完成任務" in actual_prompt
    assert "優先序" in actual_prompt

@pytest.mark.asyncio
async def test_pivot_protection_triggered():
    """
    驗證當目標不符時，代理人是否輸出 [AGENT_INPUT_NEEDED] 且不擅自決定。
    """
    task = "預訂 5/11 13:00"
    history = [{"text": "13:00 沒位置了，15:00 可以嗎？", "is_self_dom": False}]
    
    # 模擬 LLM 輸出標籤且沒有社交回覆
    mock_genai_client_inst.models.generate_content.return_value = get_mock_response(
        '[AGENT_INPUT_NEEDED, reason="時段不符，需確認替代時段"]'
    )
    
    mock_page = MagicMock()
    proxy = LineProxyEngine(page=mock_page, chat_name="娜比", task=task, api_key="fake")
    
    await proxy.generate_and_send_reply(history)
    
    # 1. 驗證標籤解析
    assert "AGENT_INPUT_NEEDED: 時段不符" in proxy.state["final_report"]
    # 2. 確保沒有發送「好的」或答應店家
    if mock_send.called:
        sent_text = mock_send.call_args[0][1]
        assert "好的" not in sent_text and "可以" not in sent_text
    else:
        # 如果沒發送任何訊息也是正確的，因為 reply_text 會是空的
        pass

@pytest.mark.asyncio
async def test_all_end_tags_exit_loop():
    """
    驗證三種終止標籤（AGENT_INPUT_NEEDED, IMPLICIT_ENDED, EXPLICIT_ENDED）
    都能正確觸發退出循環。
    """
    tags = [
        ('[AGENT_INPUT_NEEDED, reason="test"]', 120),
        ('[IMPLICIT_ENDED, reason="test"]', 300),
        ('[EXPLICIT_ENDED]', 120)
    ]
    
    for tag_text, expected_wait in tags:
        mock_genai_client_inst.models.generate_content.return_value = get_mock_response(tag_text)
        mock_page = MagicMock()
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task="task", api_key="fake")
        
        now = time.time()
        await proxy.generate_and_send_reply([{"text": "msg", "is_self_dom": False}])
        
        assert proxy.state["exit_at"] is not None
        # 容許 5 秒誤差
        assert (expected_wait - 5) < (proxy.state["exit_at"] - now) < (expected_wait + 5)
