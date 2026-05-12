import pytest
import os
import sys
import psutil
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from browser_manager import BrowserManager

@pytest.fixture
def browser_manager():
    return BrowserManager(port=9222, profile_name="test_profile")

def test_is_port_in_use(browser_manager):
    mock_conn = MagicMock()
    mock_conn.laddr.port = 9222
    mock_conn.status = 'LISTEN'
    mock_conn.pid = 1234
    
    with patch('psutil.net_connections', return_value=[mock_conn]):
        assert browser_manager.is_port_in_use() == 1234
        
    with patch('psutil.net_connections', return_value=[]):
        assert browser_manager.is_port_in_use() is None

def test_check_singleton_lock_active(browser_manager):
    with patch('pathlib.Path.is_symlink', return_value=True), \
         patch('os.readlink', return_value="some-ip-1234"), \
         patch('psutil.pid_exists', return_value=True):
        assert browser_manager.check_singleton_lock() == 1234

def test_check_singleton_lock_stale(browser_manager):
    with patch('pathlib.Path.is_symlink', return_value=True), \
         patch('os.readlink', return_value="some-ip-1234"), \
         patch('psutil.pid_exists', return_value=False), \
         patch('pathlib.Path.unlink') as mock_unlink:
        assert browser_manager.check_singleton_lock() is None
        mock_unlink.assert_called_once()

def test_check_singleton_lock_invalid_format(browser_manager):
    # Coverage for line 32-33
    with patch('pathlib.Path.is_symlink', return_value=True), \
         patch('os.readlink', return_value="badformat"), \
         patch('pathlib.Path.unlink') as mock_unlink:
        assert browser_manager.check_singleton_lock() is None
        # Unlink is still called after the try-except
        mock_unlink.assert_called_once()

def test_prepare_instance_already_running(browser_manager):
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch('httpx.get', return_value=mock_response):
        result = browser_manager.prepare_instance()
        assert result["status"] == "success"
        assert "already running" in result["message"]

def test_prepare_instance_port_occupied(browser_manager):
    with patch('httpx.get', side_effect=Exception("Connection refused")), \
         patch.object(BrowserManager, 'is_port_in_use', return_value=5555):
        result = browser_manager.prepare_instance()
        assert result["status"] == "error"
        assert "occupied by non-responsive PID 5555" in result["message"]

def test_prepare_instance_locked(browser_manager):
    with patch('httpx.get', side_effect=Exception("Connection refused")), \
         patch.object(BrowserManager, 'is_port_in_use', return_value=None), \
         patch.object(BrowserManager, 'check_singleton_lock', return_value=6666):
        result = browser_manager.prepare_instance()
        assert result["status"] == "error"
        assert "Profile locked by active PID 6666" in result["message"]

def test_prepare_instance_success_launch(browser_manager):
    mock_response_success = MagicMock()
    mock_response_success.status_code = 200
    
    with patch('httpx.get') as mock_get, \
         patch.object(BrowserManager, 'is_port_in_use', return_value=None), \
         patch.object(BrowserManager, 'check_singleton_lock', return_value=None), \
         patch('pathlib.Path.mkdir'), \
         patch('subprocess.Popen'), \
         patch('time.sleep'):
        
        mock_get.side_effect = [
            Exception("Not running"), # Initial check
            Exception("Starting..."), # Wait retry 1
            mock_response_success     # Wait retry 2
        ]
        
        result = browser_manager.prepare_instance()
        assert result["status"] == "success"
        assert result["port"] == 9222

def test_prepare_instance_failure_start(browser_manager):
    # Coverage for line 92
    with patch('httpx.get', side_effect=Exception("Never started")), \
         patch.object(BrowserManager, 'is_port_in_use', return_value=None), \
         patch.object(BrowserManager, 'check_singleton_lock', return_value=None), \
         patch('pathlib.Path.mkdir'), \
         patch('subprocess.Popen'), \
         patch('time.sleep'):
        
        result = browser_manager.prepare_instance()
        assert result["status"] == "error"
        assert "failed to start within timeout" in result["message"]
