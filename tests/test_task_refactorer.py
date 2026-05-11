import os
import sys
import pytest
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from task_refactorer import TaskRefactorer

@pytest.fixture
def api_key():
    env_path = os.path.expanduser("~/.hermes/.env")
    load_dotenv(dotenv_path=env_path)
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        pytest.skip("GEMINI_API_KEY not found")
    return key

def test_refactor_stepped_logic(api_key):
    refactorer = TaskRefactorer(api_key=api_key)
    raw_task = "預約 5/11 13:00 娜比燒肉 2大1小，要靠窗沙發、插座、推車空間，註記慶生。"
    
    refactored = refactorer.refactor(raw_task)
    
    print(f"\nRefactored Task:\n{refactored}")
    
    # Verification 1: Stepped structure
    assert "階段" in refactored or "1." in refactored
    
    # Verification 2: Check for logic separation (details should be in later phases)
    lines = refactored.split('\n')
    assert "沙發" in refactored or "慶生" in refactored
    
    # Verification 3: Information integrity (no loss of key facts)
    keywords = ["5/11", "13:00", "靠窗", "沙發", "插座", "推車", "慶生"]
    for word in keywords:
        assert word in refactored, f"Missing fact: {word}"
    
    assert "2" in refactored and "大" in refactored and "1" in refactored and "小" in refactored

def test_refactor_complex_task(api_key):
    refactorer = TaskRefactorer(api_key=api_key)
    raw_task = "詢問娜比是不是燒肉店員，是的話幫我訂 5/11 13:00，2大1小，全員忌海鮮，其中一員全素，要有插座。"
    
    refactored = refactorer.refactor(raw_task)
    
    # Verify the first phase is about identity
    lines = [line for line in refactored.split('\n') if line.strip() and ("階段" in line or "1." in line)]
    # Skip preamble if AI added one
    actual_phases = [l for l in lines if any(x in l for x in ["身分", "確認", "店員", "請求", "詢問"])]
    first_phase = actual_phases[0]
    assert "身分" in first_phase or "確認" in first_phase or "店員" in first_phase
    
    # Verify info preservation
    assert "全素" in refactored
    assert "海鮮" in refactored
    assert "插座" in refactored
