import pytest
import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from engine import LineProxyEngine

api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

@pytest.fixture(autouse=True)
def check_api_key():
    if not api_key:
        pytest.fail("CRITICAL: API KEY missing for AI intelligence test")

async def get_ai_parsed_response(task, history):
    mock_page = MagicMock()
    mock_page.bring_to_front = AsyncMock()
    with patch("line_utils.send_message", new_callable=AsyncMock), \
         patch("line_utils.extract_messages", new_callable=AsyncMock, return_value=[]), \
         patch("line_utils.select_chat", new_callable=AsyncMock, return_value={"status": "success"}):
        proxy = LineProxyEngine(page=mock_page, chat_name="test", task=task, api_key=api_key)
        
        # Build prompt from context
        context = proxy.history.get_full_context(history, [])
        prompt = proxy._build_prompt(context)
        
        # Generate and parse
        response = proxy.client.models.generate_content(model=proxy.model_name, contents=prompt)
        raw_text = str(getattr(response, 'text', '')).strip()
        parsed = proxy._parse_response(raw_text)
        return raw_text, parsed

@pytest.mark.asyncio
async def test_real_convo_embedded_summary():
    """
    REAL CONVO TEST: Verify the AI embeds accurate facts into the tag summary attribute.
    Facts used: 5/12, no sockets, self-pick nuts, no parking, no nursery.
    """
    task = """啟動一個跟店員的訂位流程。需求如下：
預約 5/11 13:00 (備選 5/12) 2大1小，需靠窗沙發、插座、推車、兒童椅、慶生蛋糕、忌海鮮堅果且一員全素、保留停車位、確認有無哺乳室。

任務完成時，標籤內的 summary 必須嚴格按以下格式彙整：
- 預約時段：日期與時間
- 設施確認：(插座/停車/哺乳室/推車/兒童椅) 的回覆
- 飲食與慶生：(蛋糕/海鮮/堅果/全素) 的具體安排
- 待辦：後續需注意的事項"""

    # ... (history messages remain the same)

    # Real facts extracted from the previous interaction logs
    history = [
        {"text": "5/12 13:00 有位子，沒問題。", "is_self_dom": False},
        {"text": "當天會盡量幫您安排靠窗沙發，沒問題。", "is_self_dom": False},
        {"text": "座位的安排上是否方便提供插座呢？", "is_self_dom": True},
        {"text": "沒有辦法喔", "is_self_dom": False},
        {"text": "是否方便提供放置嬰兒推車的空間呢？", "is_self_dom": True},
        {"text": "有的", "is_self_dom": False},
        {"text": "當天是否可以幫我們準備一份兒童椅具呢？", "is_self_dom": True},
        {"text": "好的 到時你再告知服務人員", "is_self_dom": False},
        {"text": "店內會幫你準備蛋糕", "is_self_dom": False},
        {"text": "全員忌海鮮與堅果，且一位需全素，請問方便協助安排嗎？", "is_self_dom": True},
        {"text": "堅果可能要麻煩自己挑掉 其他可以", "is_self_dom": False},
        {"text": "請問當天方便幫我們預留一個停車位嗎？", "is_self_dom": True},
        {"text": "沒有提供停車場喔", "is_self_dom": False},
        {"text": "瞭解。請問附近是否有建議的收費停車場位置與折抵規則呢？", "is_self_dom": True},
        {"text": "您可以停在林森北路上的連鎖停車場，我們沒有提供折抵喔。", "is_self_dom": False},
        {"text": "好的，謝謝您的回覆。最後想請問店內是否有提供哺乳室供客人使用呢？", "is_self_dom": True},
        {"text": "沒有 可以使用廁所", "is_self_dom": False},
        {"text": "好的，那就確認預約 5/12 13:00 共 2 大 1 小，辛苦了！", "is_self_dom": True},
        {"text": "好的 到時見", "is_self_dom": False}
    ]
    
    raw_text, parsed = await get_ai_parsed_response(task, history)
    
    print(f"\n[REAL CONVO TEST] Raw AI Response:\n{raw_text}")
    print(f"\n[REAL CONVO TEST] Extracted Summary:\n{parsed['summary']}")
    
    # Assert tag existence
    assert "[CONVERSATION_ENDED" in raw_text, f"Exit tag missing. Got: {raw_text}"
    assert "summary=" in raw_text, "Summary attribute missing in tag."
    
    # Assert specific sections in formatted summary
    summary = parsed["summary"]
    assert "預約時段" in summary
    assert "設施確認" in summary
    assert "飲食與慶生" in summary
    assert "待辦" in summary
    
    # Fact Verification within the formatted summary
    assert "5/12" in summary
    assert "堅果" in summary and any(kw in summary for kw in ["自理", "自挑", "挑除", "挑掉"])
    assert "停車" in summary and any(kw in summary for kw in ["無", "沒有", "不提供", "林森北路"])
