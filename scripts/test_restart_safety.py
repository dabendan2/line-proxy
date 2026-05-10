import pytest
from history_manager import HistoryManager

def test_startup_action_needed_is_false_when_last_msg_is_self():
    """
    確保當對話中最後一則訊息是 Hermes 自己發出的，重啟時不會重複發言。
    """
    mgr = HistoryManager(chat_name="test_restart_safety")
    # 模擬 DOM 訊息：最新的一則（index 0）是自己發的
    msgs = [
        {"text": "您好，我是 Hermes。請問 5/11 還有位子嗎？", "is_self_dom": True, "has_hermes_prefix": True},
        {"text": "您好，請問有什麼需要服務的嗎？", "is_self_dom": False, "has_hermes_prefix": False},
    ]
    task = "啟動訂位流程"

    state = mgr.rebuild_state(msgs, task)

    # 預期：不該自動觸發，且記錄最後處理訊息
    assert state["startup_action_needed"] is False
    assert state["last_processed_msg"] == "您好，我是 Hermes。請問 5/11 還有位子嗎？"

def test_startup_action_needed_is_true_when_last_msg_is_user():
    """
    確保當最後一則訊息是使用者發出的，重啟後能立刻接手回覆。
    """
    mgr = HistoryManager(chat_name="test_takeover_safety")
    msgs = [
        {"text": "有位子喔，請問幾位？", "is_self_dom": False, "has_hermes_prefix": False},
        {"text": "您好，我是 Hermes。請問 5/11 還有位子嗎？", "is_self_dom": True, "has_hermes_prefix": True},
    ]
    task = "啟動訂位流程"

    state = mgr.rebuild_state(msgs, task)

    assert state["startup_action_needed"] is True
    assert state["last_processed_msg"] == "___FRESH_TAKEOVER___"
