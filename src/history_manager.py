import os
import re
import time
from datetime import datetime

class HistoryManager:
    def __init__(self, chat_name):
        log_dir = os.path.expanduser("~/.line-proxy/logs")
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, f"{chat_name}.log")

    def write_log(self, msg):
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{t}] {msg}", flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{t}] {msg}\n")

    def rebuild_state(self, msgs, task_description):
        # We still need to identify what was previously sent to avoid duplicate replies
        # if the process is restarted.
        sent_messages = []
        
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if " SENT: " in line:
                        text = line.split(" SENT: ", 1)[1].strip()
                        sent_messages.append(text)

        # Older messages are first in msgs list
        for m in msgs:
            if m["is_self_dom"] and m["text"].strip() not in sent_messages:
                sent_messages.append(m["text"].strip())

        state = {
            "last_processed_msg": "",
            "sent_messages": sent_messages,
            "exit_at": None,
            "startup_action_needed": False
        }

        if msgs:
            # Chronological: newest is at the end
            latest = msgs[-1]
            is_hermes = latest.get("has_hermes_prefix", False) or latest.get("is_self_dom", False)
            
            # If the last message was NOT from Hermes, we should check if action is needed
            if not is_hermes:
                state["startup_action_needed"] = True
                state["last_processed_msg"] = "___TAKEOVER___"
            else:
                state["startup_action_needed"] = False
                state["last_processed_msg"] = latest["text"]
        else:
            state["startup_action_needed"] = True

        return state

    def get_full_context(self, msgs, sent_messages):
        dom_history = []
        
        # msgs is chronological (Oldest First)
        # Includes ALL messages provided by line_utils.extract_messages
        for m in msgs:
            text = m["text"].strip()
            timestamp = m.get("timestamp", "Unknown Time")
            is_hermes = m.get("is_self_dom", False)
            sender = "Hermes (AI Proxy)" if is_hermes else "User/Staff"
            
            dom_history.append(f"[{timestamp}] {sender}: {text}")

        return dom_history
