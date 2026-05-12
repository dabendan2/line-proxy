import pytest
import os
import sys
import psutil
from unittest.mock import MagicMock, patch, mock_open, PropertyMock
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from reset_proxy import main

@pytest.fixture
def mock_psutil_tools():
    with patch('psutil.pid_exists') as m_pid, \
         patch('psutil.Process') as m_proc, \
         patch('psutil.process_iter') as m_iter:
        yield m_pid, m_proc, m_iter

@pytest.fixture
def mock_fs_tools():
    with patch('pathlib.Path.exists') as m_exists, \
         patch('os.remove') as m_remove:
        yield m_exists, m_remove

def test_reset_proxy_full_cleanup(mock_psutil_tools, mock_fs_tools):
    m_pid, m_proc_class, m_iter = mock_psutil_tools
    m_exists, m_remove = mock_fs_tools
    
    with patch('reset_proxy.argparse.ArgumentParser.parse_args') as m_args:
        args = MagicMock()
        args.chat = "Test Chat!"
        args.clear_log = True
        m_args.return_value = args
        
        m_exists.side_effect = [True, True]
        m_pid.return_value = True
        proc = MagicMock()
        proc.name.return_value = "python3"
        m_proc_class.return_value = proc
        
        stray = MagicMock()
        stray.info = {'pid': 9999, 'cmdline': ['python', 'run_engine.py', '--chat', 'Test Chat!']}
        m_iter.return_value = [stray]
        
        with patch('builtins.open', mock_open(read_data="1234")):
            main()
            
        proc.kill.assert_called_once()
        stray.kill.assert_called_once()
        m_remove.assert_any_call(Path.home() / ".line-proxy" / "locks" / "Test_Chat_.pid")
        m_remove.assert_any_call(Path.home() / ".line-proxy" / "logs" / "Test Chat!.log")

def test_reset_proxy_non_python_proc(mock_psutil_tools, mock_fs_tools):
    m_pid, m_proc_class, m_iter = mock_psutil_tools
    m_exists, m_remove = mock_fs_tools
    
    with patch('reset_proxy.argparse.ArgumentParser.parse_args') as m_args:
        args = MagicMock()
        args.chat = "NonPython"
        args.clear_log = False
        m_args.return_value = args
        
        m_exists.return_value = True
        m_pid.return_value = True
        proc = MagicMock()
        proc.name.return_value = "bash"
        m_proc_class.return_value = proc
        m_iter.return_value = []
        
        with patch('builtins.open', mock_open(read_data="1234")):
            main()
            
        proc.kill.assert_not_called()
        m_remove.assert_called_once()

def test_reset_proxy_lock_read_error(mock_psutil_tools, mock_fs_tools):
    m_pid, m_proc_class, m_iter = mock_psutil_tools
    m_exists, m_remove = mock_fs_tools
    
    with patch('reset_proxy.argparse.ArgumentParser.parse_args') as m_args:
        args = MagicMock()
        args.chat = "ErrorRead"
        args.clear_log = False
        m_args.return_value = args
        
        m_exists.return_value = True
        m_iter.return_value = []
        
        with patch('builtins.open', side_effect=Exception("Perm error")):
            main()
            
        m_remove.assert_called_once()

def test_reset_proxy_stray_error(mock_psutil_tools, mock_fs_tools):
    m_pid, m_proc_class, m_iter = mock_psutil_tools
    m_exists, m_remove = mock_fs_tools
    
    with patch('reset_proxy.argparse.ArgumentParser.parse_args') as m_args:
        args = MagicMock()
        args.chat = "StrayError"
        args.clear_log = False
        m_args.return_value = args
        m_exists.return_value = False
        
        bad_proc = MagicMock()
        type(bad_proc).info = PropertyMock(side_effect=psutil.NoSuchProcess(123))
        m_iter.return_value = [bad_proc]
        
        main()
