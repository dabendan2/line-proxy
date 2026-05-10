import json
import shlex
from hermes_tools import terminal

def test_blocking_mcp_with_notification():
    chat_name = "dabendan.test"
    task_description = "[TEST] Start a tic-tac-toe game. Just send the board and wait. If user replies 'exit', end task."
    
    # 1. Clean up existing locks
    terminal(f"rm -f /home/ubuntu/line-proxy/.locks/{chat_name}.lock")
    
    # 2. Build the command
    # We use mcporter call line_proxy.run_task
    # We MUST escape quotes correctly for shell
    args = {
        "chat_name": chat_name,
        "task": task_description
    }
    args_json = json.dumps(args)
    
    cmd = f"npx mcporter call line_proxy.run_task --args {shlex.quote(args_json)} --output json"
    
    print(f"Launching blocking task via terminal background: {cmd}")
    
    # 3. Use terminal background with notification
    # This is the NEW pattern
    res = terminal(
        command=cmd,
        background=True,
        notify_on_complete=True
    )
    
    print(f"Terminal Result: {json.dumps(res, indent=2)}")
    print("Test triggered. You should receive a notification when the task completes.")

if __name__ == "__main__":
    test_blocking_mcp_with_notification()
