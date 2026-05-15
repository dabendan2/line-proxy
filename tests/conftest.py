import sys
import os

# Automatically add src/ to sys.path so tests can find the package
# This removes the need for 'export PYTHONPATH' when running pytest
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(base_dir, "src")

if src_path not in sys.path:
    sys.path.insert(0, src_path)
