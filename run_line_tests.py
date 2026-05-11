import pytest
import sys
import os
from dotenv import load_dotenv
from pathlib import Path

# Add src/ to path so engine, line_utils, etc. can be imported
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, "src"))

# Load environment variables from ~/.hermes/.env
env_path = Path.home() / ".hermes" / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

if __name__ == "__main__":
    # Guidance for Hermes Agent
    print("\n" + "="*60)
    print("  [HINT] Running full test suite including REAL AI integration tests.")
    print("  [HINT] Please ensure terminal() timeout is set to 180s (3 minutes).")
    print("="*60 + "\n")
    
    # Run pytest on the tests/ directory
    sys.exit(pytest.main(["tests/"]))
