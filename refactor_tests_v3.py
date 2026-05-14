import os
import re

test_dir = '/home/ubuntu/chat-agent/tests'

def update_test_files():
    for root, dirs, files in os.walk(test_dir):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                new_content = content
                
                # Modules to subpackages mapping
                mapping = {
                    'line_utils': 'channels.line.driver',
                    'engine': 'core.engine',
                    'history_manager': 'core.history',
                    'reset_proxy': 'channels.line.proxy',
                    'run_engine': 'channels.line.run_engine',
                    'browser_manager': 'utils.browser',
                    'lock_manager': 'utils.locker',
                    'config': 'utils.config',
                }
                
                for old, new in mapping.items():
                    # Handle patch('module.
                    new_content = re.sub(fr"patch\(['\"]{old}\.", f"patch('{new}.", new_content)
                    # Handle unittest.mock.patch('module
                    new_content = re.sub(fr"unittest\.mock\.patch\(['\"]{old}", f"unittest.mock.patch('{new}", new_content)
                
                # Fix paths
                new_content = re.sub(r'os\.path\.join\(os\.path\.dirname\(__file__\), "..", "src", "line_utils\.py"\)',
                                     r'os.path.join(os.path.dirname(__file__), "../../../src/channels/line/driver.py")', new_content)
                new_content = new_content.replace('src/line_utils.py', 'src/channels/line/driver.py')
                new_content = new_content.replace('src/engine.py', 'src/core/engine.py')
                
                # Fix .line-proxy to .chat-agent in tests too
                new_content = new_content.replace('.line-proxy', '.chat-agent')
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    print(f"Updated test: {path}")

update_test_files()
