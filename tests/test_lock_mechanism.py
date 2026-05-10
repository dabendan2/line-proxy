import pytest
import os
import time
import subprocess
import sys
from lock_manager import PIDLock

def test_lock_acquisition_and_release():
    """驗證 Lock 的獲取與釋放。"""
    chat_name = "test_lock_1"
    lock = PIDLock(chat_name)
    
    # 確保初始狀態沒有 lock
    if os.path.exists(lock.lock_path):
        os.remove(lock.lock_path)
        
    # 1. 第一次獲取應成功
    assert lock.acquire() is True
    assert os.path.exists(lock.lock_path)
    
    # 2. 第二次獲取應失敗 (同一進程也會失敗，因為我們檢查 PID 是否存在)
    lock2 = PIDLock(chat_name)
    assert lock2.acquire() is False
    
    # 3. 釋放後應成功
    lock.release()
    assert not os.path.exists(lock.lock_path)
    assert lock2.acquire() is True
    lock2.release()

def test_stale_lock_recovery():
    """驗證當 PID 不存在時（Stale Lock），新進程能自動接手。"""
    chat_name = "test_stale"
    lock = PIDLock(chat_name)
    
    # 手動寫入一個不可能存在的巨大 PID
    os.makedirs(os.path.dirname(lock.lock_path), exist_ok=True)
    with open(lock.lock_path, "w") as f:
        f.write("9999999") 
        
    # 獲取應成功（自動蓋掉過期 lock）
    assert lock.acquire() is True
    with open(lock.lock_path, "r") as f:
        assert f.read().strip() == str(os.getpid())
    
    lock.release()
