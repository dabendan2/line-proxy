import os
import re

def fix_engine():
    path = "/home/ubuntu/chat-agent/src/core/engine.py"
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the triple os.path.dirname mess
    content = re.sub(r'os\.path\.join\(os\.path\.dirname\(__file__\), os\.path\.join\(os\.path\.dirname\(__file__\), os\.path\.join\(os\.path\.dirname\(__file__\), "prompts/(.*?)"\)\)\)', 
                     r'os.path.join(os.path.dirname(__file__), "prompts/\1")', content)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_refactorer():
    path = "/home/ubuntu/chat-agent/src/core/refactorer.py"
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = re.sub(r'os\.path\.join\(os\.path\.dirname\(__file__\), os\.path\.join\(os\.path\.dirname\(__file__\), os\.path\.join\(os\.path\.dirname\(__file__\), "prompts/(.*?)"\)\)\)', 
                     r'os.path.join(os.path.dirname(__file__), "prompts/\1")', content)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

fix_engine()
fix_refactorer()
print("Fixed prompt paths.")
