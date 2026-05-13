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

def test_prepare_instance_already_running_with_extension(browser_manager):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"url": "chrome-extension://ophjlpahpchlmihnnnihgmmeilfjmjjc/index.html"}]
    
    mock_proc = MagicMock()
    mock_proc.cmdline.return_value = ["chromium", "--user-data-dir=" + str(browser_manager.user_data_dir)]
    
    with patch('httpx.get', return_value=mock_response), \
         patch.object(BrowserManager, 'is_port_in_use', return_value=1234), \
         patch('psutil.Process', return_value=mock_proc):
        result = browser_manager.prepare_instance()
        assert result["status"] == "success"
        assert result["port"] == 9222

def test_prepare_instance_already_running_no_extension(browser_manager):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"url": "about:blank"}]
    
    mock_proc = MagicMock()
    mock_proc.cmdline.return_value = ["chromium", "--user-data-dir=" + str(browser_manager.user_data_dir)]
    
    with patch('httpx.get', return_value=mock_response), \
         patch.object(BrowserManager, 'is_port_in_use', return_value=1234), \
         patch('psutil.Process', return_value=mock_proc):
        result = browser_manager.prepare_instance()
        assert result["status"] == "success"
        assert "navigation may be needed" in result["message"]

def test_prepare_instance_cleanup_zombie(browser_manager):
    mock_proc = MagicMock()
    mock_proc.name.return_value = "chromium-browser"
    
    with patch('httpx.get', side_effect=Exception("Connection refused")), \
         patch.object(BrowserManager, 'is_port_in_use', return_value=5555), \
         patch('psutil.Process', return_value=mock_proc), \
         patch.object(BrowserManager, 'check_singleton_lock', return_value=None), \
         patch('pathlib.Path.mkdir'), \
         patch('subprocess.Popen'), \
         patch('time.sleep'), \
         patch('httpx.get', side_effect=[Exception("Refused"), MagicMock(status_code=200, json=lambda: [{"url": "ext"}])]):
        
        result = browser_manager.prepare_instance()
        assert result["status"] == "success"
        mock_proc.terminate.assert_called_once()

def test_prepare_instance_cleanup_lock(browser_manager):
    mock_proc = MagicMock()
    
    with patch('httpx.get', side_effect=Exception("Connection refused")), \
         patch.object(BrowserManager, 'is_port_in_use', return_value=None), \
         patch.object(BrowserManager, 'check_singleton_lock', return_value=6666), \
         patch('psutil.Process', return_value=mock_proc), \
         patch('pathlib.Path.unlink'), \
         patch('pathlib.Path.mkdir'), \
         patch('subprocess.Popen'), \
         patch('time.sleep'), \
         patch('httpx.get', side_effect=[Exception("Refused"), MagicMock(status_code=200, json=lambda: [{"url": "ext"}])]):
        
        result = browser_manager.prepare_instance()
        assert result["status"] == "success"
        mock_proc.terminate.assert_called_once()

def test_prepare_instance_failure_start(browser_manager):
    with patch('httpx.get', side_effect=Exception("Never started")), \
         patch.object(BrowserManager, 'is_port_in_use', return_value=None), \
         patch.object(BrowserManager, 'check_singleton_lock', return_value=None), \
         patch('pathlib.Path.mkdir'), \
         patch('subprocess.Popen'), \
         patch('time.sleep'):
        
        result = browser_manager.prepare_instance()
        assert result["status"] == "error"
        assert "failed to start within timeout" in result["message"]
