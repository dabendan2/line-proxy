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

def check_timeout_safety():
    """
    Mandatory safety check for Hermes Agent execution.
    Ensures that the agent has explicitly declared a sufficient timeout 
    to prevent orphan processes or incomplete test runs.
    """
    is_hermes = os.environ.get("_HERMES_GATEWAY") == "1"
    if is_hermes:
        try:
            timeout_val = int(os.environ.get("TIMEOUT_SET", 0))
        except ValueError:
            timeout_val = 0
            
        if timeout_val < 180:
            print("\n" + "!"*60)
            print("  [ERROR] PLATFORM SAFETY VIOLATION")
            print("  Detected execution via Hermes Gateway without sufficient timeout.")
            print("  ")
            print("  REQUIRED ACTION:")
            print("  You MUST explicitly set TIMEOUT_SET=180 in your command AND")
            print("  use terminal(timeout=180) to match it.")
            print("  ")
            print("  Example:")
            print("  terminal(command='export TIMEOUT_SET=180 && git commit ...', timeout=180)")
            print("!"*60 + "\n")
            sys.exit(1)

if __name__ == "__main__":
    # Perform safety check first
    check_timeout_safety()

    # Guidance for Hermes Agent
    print("\n" + "="*60)
    print("  [HINT] Running full test suite including REAL AI integration tests.")
    print("  [HINT] Safety Check Passed: TIMEOUT_SET >= 180s")
    print("="*60 + "\n")
    
    # Run pytest on the tests/ directory
    sys.exit(pytest.main(["tests/"]))
