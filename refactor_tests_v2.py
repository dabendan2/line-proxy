import os
import re

test_dir = '/home/ubuntu/chat-agent/tests'

replacements = {
    # String literal patches in unittest.mock.patch
    r"unittest\.mock\.patch\('line_utils": r"unittest.mock.patch('channels.line.driver",
    r"unittest\.mock\.patch\('engine": r"unittest.mock.patch('core.engine",
    r"unittest\.mock\.patch\('history_manager": r"unittest.mock.patch('core.history",
    r"unittest\.mock\.patch\('reset_proxy": r"unittest.mock.patch('channels.line.proxy",
    r"unittest\.mock\.patch\('run_engine": r"unittest.mock.patch('channels.line.run_engine",
    r"unittest\.mock\.patch\('browser_manager": r"unittest.mock.patch('utils.browser",
    r"unittest\.mock\.patch\('lock_manager": r"unittest.mock.patch('utils.locker",
    
    # Generic patch strings
    r'patch\("line_utils\.': r'patch("channels.line.driver.',
    r'patch\("engine\.': r'patch("core.engine.',
    r'patch\("history_manager\.': r'patch("core.history.',
    r'patch\("reset_proxy\.': r'patch("channels.line.proxy.',
    r'patch\("run_engine\.': r'patch("channels.line.run_engine.',
    r'patch\("browser_manager\.': r'patch("utils.browser.',
    r'patch\("lock_manager\.': r'patch("utils.locker.',
}

def update_test_files():
    for root, dirs, files in os.walk(test_dir):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                new_content = content
                for old, new in replacements.items():
                    new_content = re.sub(old, new, new_content)
                
                # Fix specific path logic in test_order_logic.py and others
                # Current: os.path.join(os.path.dirname(__file__), "..", "src", "line_utils.py")
                # Should be: os.path.join(os.path.dirname(__file__), "../../..", "src", "channels/line/driver.py")
                new_content = re.sub(r'os\.path\.join\(os\.path\.dirname\(__file__\), "..", "src", "line_utils\.py"\)',
                                     r'os.path.join(os.path.dirname(__file__), "../../../src/channels/line/driver.py")', new_content)
                
                # Also handle variations
                new_content = new_content.replace('src/line_utils.py', 'src/channels/line/driver.py')
                new_content = new_content.replace('src/engine.py', 'src/core/engine.py')
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    print(f"Updated test: {path}")

update_test_files()
