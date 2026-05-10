import json
import shlex
import time
from hermes_tools import terminal

def call_mcp(tool, **kwargs):
    """Helper to call MCP via mcporter with robust JSON arg passing."""
    args_json = json.dumps(kwargs)
    cmd = f"npx mcporter call line_proxy.{tool} --args {shlex.quote(args_json)} --output json"
    res = terminal(cmd)
    try:
        return json.loads(res['output'])
    except:
        return res['output']

def game_loop(chat_name, initial_state, process_move_fn, render_fn):
    """
    Generic loop for turn-based games on LINE.
    :param chat_name: Target chat.
    :param initial_state: The starting board/state.
    :param process_move_fn: (state, user_text) -> (new_state, agent_move_desc)
    :param render_fn: (state) -> printable_string
    """
    state = initial_state
    
    # Send intro
    intro = f"Game Start!\n\n{render_fn(state)}"
    call_mcp("send_line_message", chat_name=chat_name, text=intro)
    
    while True:
        # 1. Wait for user input
        print(f"Waiting for input in {chat_name}...")
        time.sleep(10) # Simple poll
        
        msgs = call_mcp("get_line_messages", chat_name=chat_name, limit=5)
        if not isinstance(msgs, dict) or msgs.get('status') != 'success':
            continue
            
        latest = msgs['messages'][-1]
        if latest.get('is_self_dom'):
            continue # Last message was ours
            
        user_text = latest.get('text', '').strip()
        
        # 2. Process move
        new_state, desc = process_move_fn(state, user_text)
        if new_state == state: # Invalid move or no change
            continue
            
        state = new_state
        
        # 3. Respond
        reply = f"You said: {user_text}\n{desc}\n\n{render_fn(state)}"
        call_mcp("send_line_message", chat_name=chat_name, text=reply)
        
        # Add termination logic here (win/loss/exit)
        if "Game Over" in desc:
            break
