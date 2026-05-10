import pytest
import os
import sys
import psutil
import time

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from lock_manager import PIDLock

def test_lock_acquisition_and_release():
    lock_name = "test_lock_unique_123"
    lock = PIDLock(lock_name)
    
    # Force cleanup
    if os.path.exists(lock.lock_path):
        os.remove(lock.lock_path)
    
    # 1. First acquire should succeed
    success = lock.acquire()
    assert success is True, "First acquire should succeed"
    assert os.path.exists(lock.lock_path)
    
    # 2. Second acquire (same name) should fail because PID is active (ourselves)
    lock2 = PIDLock(lock_name)
    success2 = lock2.acquire()
    assert success2 is False, "Second acquire should fail"
    
    # 3. Release should remove file
    lock.release()
    assert not os.path.exists(lock.lock_path)

def test_stale_lock_recovery():
    lock_name = "stale_test_recover"
    lock = PIDLock(lock_name)
    
    # Cleanup
    if os.path.exists(lock.lock_path):
        os.remove(lock.lock_path)
        
    # Create a fake lock file with a PID that is definitely NOT running or not python
    # Using a very high PID is usually safe for "not running"
    fake_pid = 999999
    while psutil.pid_exists(fake_pid):
        fake_pid += 1
        
    os.makedirs(os.path.dirname(lock.lock_path), exist_ok=True)
    with open(lock.lock_path, "w") as f:
        f.write(str(fake_pid))
    
    # New instance should be able to recover because fake_pid is dead
    lock2 = PIDLock(lock_name)
    assert lock2.acquire() is True, "Should recover from stale lock"
    
    lock2.release()
