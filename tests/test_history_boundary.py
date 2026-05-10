import pytest
from history_manager import HistoryManager

def test_history_context_filtering_with_ignored_msg():
    """驗證 get_full_context 是否能精準排除 last_ignored_msg 及其之前的訊息。"""
    # Arrange
    mgr = HistoryManager(chat_name="test", last_ignored_msg="忽略我", last_ignored_time="10:00 AM")
    
    # 模擬 DOM 訊息（reversed 順序，index 0 是最新）
    msgs = [
        {"text": "新訊息 2", "time": "10:10 AM", "is_self_dom": False},
        {"text": "新訊息 1", "time": "10:05 AM", "is_self_dom": False},
        {"text": "忽略我", "time": "10:00 AM", "is_self_dom": False}, # 邊界訊息
        {"text": "老訊息", "time": "09:55 AM", "is_self_dom": False},
    ]
    
    sent_messages = [] # 假設沒有 SENT log
    
    # Act
    context = mgr.get_full_context(msgs, sent_messages)
    
    # Assert
    # 預期 context 只包含 "新訊息 1" 和 "新訊息 2"
    # 注意：get_full_context 內部的 dom_history 是依照 reversed(msgs) 的順序處理，
    # 但 found_start 之後才會開始 append。
    assert len(context) == 2
    assert "User/Staff: 新訊息 1" in context[0]
    assert "User/Staff: 新訊息 2" in context[1]
    assert "User/Staff: 忽略我" not in "".join(context)
    assert "User/Staff: 老訊息" not in "".join(context)

def test_history_context_without_ignored_msg():
    """驗證當沒有 last_ignored_msg 時，應該包含所有可見訊息。"""
    mgr = HistoryManager(chat_name="test", last_ignored_msg=None)
    msgs = [
        {"text": "最新", "time": "10:10 AM", "is_self_dom": False},
        {"text": "最舊", "time": "09:55 AM", "is_self_dom": False},
    ]
    context = mgr.get_full_context(msgs, [])
    
    assert len(context) == 2
    assert "User/Staff: 最舊" in context[0]
    assert "User/Staff: 最新" in context[1]
