import pytest
from history_manager import HistoryManager

def test_startup_action_needed_is_false_when_last_msg_is_self():
    """
    單元測試：確保當 DOM 中最後一則訊息是 Hermes 自己發出的（有 prefix 或 is_self_dom），
    rebuild_state 應該判定 startup_action_needed 為 False，防止重啟後重複發言。
    """
    # Arrange
    mgr = HistoryManager(chat_name="test_startup")
    # 模擬 DOM 訊息：最新的一則（index 0）是自己發的
    msgs = [
        {"text": "您好，我是 Hermes。請問 5/11 還有位子嗎？", "is_self_dom": True, "has_hermes_prefix": True},
        {"text": "您好，請問有什麼需要服務的嗎？", "is_self_dom": False, "has_hermes_prefix": False},
    ]
    task = "啟動訂位流程"

    # Act
    state = mgr.rebuild_state(msgs, task)

    # Assert
    # 預期：既然最後一則是自己發的，就不該在啟動時自動觸發回覆
    assert state["startup_action_needed"] is False
    # 預期：last_processed_msg 應該被更新為最後一則內容，避免重複處理
    assert state["last_processed_msg"] == "您好，我是 Hermes。請問 5/11 還有位子嗎？"

def test_startup_action_needed_is_true_when_last_msg_is_user():
    """
    單元測試：確保當 DOM 中最後一則訊息是使用者發出的，
    rebuild_state 應該判定 startup_action_needed 為 True，確保即時回覆。
    """
    # Arrange
    mgr = HistoryManager(chat_name="test_startup_user")
    # 模擬 DOM 訊息：最新的一則是使用者發的
    msgs = [
        {"text": "有位子喔，請問幾位？", "is_self_dom": False, "has_hermes_prefix": False},
        {"text": "您好，我是 Hermes。請問 5/11 還有位子嗎？", "is_self_dom": True, "has_hermes_prefix": True},
    ]
    task = "啟動訂位流程"

    # Act
    state = mgr.rebuild_state(msgs, task)

    # Assert
    assert state["startup_action_needed"] is True
    assert state["last_processed_msg"] == "___FRESH_TAKEOVER___"
