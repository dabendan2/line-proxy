import pytest
import sys
import os

# Add src/ to path so engine, line_utils, etc. can be imported
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, "src"))

if __name__ == "__main__":
    # Run pytest on the tests/ directory
    sys.exit(pytest.main(["tests/"]))
