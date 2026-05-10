import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
import time

# Ensure engine can be imported from parent scripts dir or absolute path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

# Mocks
mock_extract = AsyncMock()
mock_send = AsyncMock()
mock_genai_client_inst = MagicMock()
mock_genai_client_class = MagicMock(return_value=mock_genai_client_inst)

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
    Verify agent doesn't dump all info at once.
    """
    complex_task = "預訂5/11 13:00 2大2小 要求1個兒童餐具 及保留停車位。訂位資訊 賴俊羽 0958078550"
    
    mock_genai_client_inst.models.generate_content.return_value = get_mock_response(
        "您好，我是 俊羽 的 AI 代理。想預訂 5/11 13:00 還有位置嗎？ [WAIT_FOR_USER_INPUT]"
    )
    
    mock_page = MagicMock()
    proxy = LineProxyEngine(page=mock_page, chat_name="Shop", task=complex_task, api_key="fake")
    
    await proxy.generate_and_send_reply([]) 
    
    mock_send.assert_called_once()
    sent_text = mock_send.call_args[0][1]
    
    assert "0958078550" not in sent_text
    assert "兒童餐具" not in sent_text
    assert len(sent_text) <= 40

@pytest.mark.asyncio
async def test_pivot_protection_triggered():
    """
    Verify [AGENT_INPUT_NEEDED] triggers on unavailable target time.
    """
    task = "預訂 5/11 13:00"
    history = [{"text": "13:00 沒位置了，15:00 可以嗎？", "is_self_dom": False}]
    
    mock_genai_client_inst.models.generate_content.return_value = get_mock_response(
        '[AGENT_INPUT_NEEDED, reason="時段不符，需確認替代時段"]'
    )
    
    mock_page = MagicMock()
    proxy = LineProxyEngine(page=mock_page, chat_name="Shop", task=task, api_key="fake")
    
    await proxy.generate_and_send_reply(history)
    assert "AGENT_INPUT_NEEDED: 時段不符" in proxy.state["final_report"]
