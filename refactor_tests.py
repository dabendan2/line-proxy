import os
import re

test_dir = '/home/ubuntu/chat-agent/tests'

replacements = {
    # Imports
    r'import line_utils': r'from channels.line import driver as line_utils',
    r'from line_utils import': r'from channels.line.driver import',
    r'import browser_manager': r'from utils import browser as browser_manager',
    r'from browser_manager import': r'from utils.browser import',
    r'import lock_manager': r'from utils import locker as lock_manager',
    r'from lock_manager import': r'from utils.locker import',
    r'import engine': r'from core import engine',
    r'from engine import': r'from core.engine import',
    r'import history_manager': r'from core import history as history_manager',
    r'from history_manager import': r'from core.history import',
    r'import task_refactorer': r'from core import refactorer as task_refactorer',
    r'from task_refactorer import': r'from core.refactorer import',
    r'import reset_proxy': r'from channels.line import proxy as reset_proxy',
    r'from reset_proxy import': r'from channels.line.proxy import',
    r'import run_engine': r'from channels.line import run_engine',
    r'from run_engine import': r'from channels.line.run_engine import',
    
    # Patch strings
    r'patch\("line_utils\.': r'patch("channels.line.driver.',
    r'patch\("browser_manager\.': r'patch("utils.browser.',
    r'patch\("lock_manager\.': r'patch("utils.locker.',
    r'patch\("engine\.': r'patch("core.engine.',
    r'patch\("history_manager\.': r'patch("core.history.',
    r'patch\("task_refactorer\.': r'patch("core.refactorer.',
    r'patch\("reset_proxy\.': r'patch("channels.line.proxy.',
    r'patch\("run_engine\.': r'patch("channels.line.run_engine.',
    r'patch\("mcp_server\.': r'patch("mcp_server.', # top level remains
}

def update_test_files():
    for root, dirs, files in os.walk(test_dir):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Correcting mistake in thought: use a different var for content
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                new_content = content
                for old, new in replacements.items():
                    new_content = re.sub(old, new, new_content)
                
                # Fix the FileNotFoundError in tests: ../src/line_utils.py etc
                new_content = new_content.replace('src/line_utils.py', 'src/channels/line/driver.py')
                new_content = new_content.replace('src/engine.py', 'src/core/engine.py')
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    print(f"Updated test: {path}")

update_test_files()
