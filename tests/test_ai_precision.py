import pytest
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from engine import LineProxyEngine

# Mock page
class MockPage:
    async def bring_to_front(self): pass

@pytest.fixture(autouse=True)
def api_key():
    env_path = os.path.expanduser("~/.hermes/.env")
    load_dotenv(dotenv_path=env_path)
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        pytest.fail("CRITICAL: API KEY missing for AI intelligence test")
    return key

async def run_ai_test(task, history_msgs):
    # Setup engine
    engine = LineProxyEngine(page=MockPage(), chat_name="Test", task=task)
    
    # Simulate first turn
    prompt = engine._build_prompt(history_msgs)
    response = engine.client.models.generate_content(model=engine.model_name, contents=prompt)
    return response.text.strip()

@pytest.mark.asyncio
async def test_ai_precision_question():
    """
    Verify the AI provides PRECISE info in its question while adhering to Stepped Communication.
    """
    task = """1. **階段：確認身份** - 確認聯繫對象是否為「娜比燒肉」。
2. **階段：預約** - 預約 5/11 13:00 2大1小。"""

    # Fresh start, no history
    history = []

    out = await run_ai_test(task, history)

    print(f"\n[PRECISION TEST] AI Response: {out}")

    # Negative test: should not leak details too early
    assert "13:00" not in out, "AI leaked time in identity check."
    assert "2大1小" not in out, "AI leaked pax in identity check."

    # Positive test: Identity confirmation
    assert "娜比燒肉" in out, "AI failed to mention the restaurant name in its identity check."
    assert "請問" in out or "是否" in out, "AI failed to ask a question for identity confirmation."
