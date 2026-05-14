import pytest
import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from dotenv import load_dotenv

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from core.engine import ChatEngine

# Load env explicitly
load_dotenv(dotenv_path=Path.home() / ".hermes" / ".env")

TEST_KEY_VALUE = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "MISSING"

class MockResponse:
    def __init__(self, text):
        self.text = text

async def get_ai_parsed_response(task, history):
    mock_page = MagicMock()
    mock_page.bring_to_front = AsyncMock()
    with patch("channels.line.driver.send_message", new_callable=AsyncMock), \
         patch("channels.line.driver.extract_messages", new_callable=AsyncMock, return_value=[]), \
         patch("channels.line.driver.select_chat", new_callable=AsyncMock, return_value={"status": "success"}):
        mock_channel = AsyncMock(); proxy = ChatEngine(channel=mock_channel, chat_name="test", task=task, api_key=TEST_KEY_VALUE)
        context = proxy.history.get_full_context(history, [])
        prompt = proxy._build_prompt(context)
        response = proxy.client.models.generate_content(model=proxy.model_name, contents=prompt)
        raw_text = str(getattr(response, 'text', '')).strip()
        parsed = proxy._parse_response(raw_text)
        return raw_text, parsed

@pytest.mark.asyncio
async def test_unified_conversation_ended_tag():
    task = "簡單訂位"
    history = [
        {"text": "5/12 13:00 有位子嗎？", "sender": "俊羽"},
        {"text": "有的，已保留。", "sender": "Chat"},
        {"text": "好的，謝謝！", "sender": "Hermes"}
    ]
    raw_text, parsed = await get_ai_parsed_response(task, history)
    assert "[CONVERSATION_ENDED" in raw_text
    assert "summary=" in raw_text
    assert parsed["conversation_ended"] is True

@pytest.mark.asyncio
async def test_last_summary_overwrites():
    mock_page = MagicMock()
    mock_page.bring_to_front = AsyncMock()
    with patch("channels.line.driver.send_message", new_callable=AsyncMock), \
         patch("channels.line.driver.extract_messages", new_callable=AsyncMock, return_value=[]), \
         patch("channels.line.driver.select_chat", new_callable=AsyncMock, return_value={"status": "success"}):
        mock_channel = AsyncMock(); proxy = ChatEngine(channel=mock_channel, chat_name="test", task="測試彙整覆蓋", api_key=TEST_KEY_VALUE)
        res1 = MockResponse('再見。[CONVERSATION_ENDED, summary="報告A"]')
        with patch.object(proxy.client.models, 'generate_content', return_value=res1):
            await proxy.generate_and_send_reply([])
            assert proxy.state.get("final_report") == "Conversation ended."
        res2 = MockResponse('好的沒問題。[CONVERSATION_ENDED, summary="報告B"]')
        result = proxy._parse_response(res2.text)
        assert result["summary"] == "報告B"
