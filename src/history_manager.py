import os
import time
from config import LOG_DIR

class HistoryManager:
    def __init__(self, chat_name):
        self.log_path = LOG_DIR / f"{chat_name}.log"

    def write_log(self, msg):
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{t}] {msg}", flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{t}] {msg}\n")

    def rebuild_state(self, msgs, task_description):
        sent_messages = []
        
        if self.log_path.exists():
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if " SENT: " in line:
                        text = line.split(" SENT: ", 1)[1].strip()
                        sent_messages.append(text)

        for m in msgs:
            text = m["text"].strip()
            if m["is_self_dom"] and text not in sent_messages:
                sent_messages.append(text)

        state = {
            "last_processed_msg": "",
            "sent_messages": sent_messages,
            "exit_at": None,
            "startup_action_needed": False
        }

        if msgs:
            latest = msgs[-1]
            is_hermes = latest.get("has_hermes_prefix", False) or latest.get("is_self_dom", False)
            
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
        for m in msgs:
            text = m["text"].strip()
            timestamp = m.get("timestamp", "Unknown Time")
            is_hermes = m.get("is_self_dom", False)
            sender = "Hermes (AI Proxy)" if is_hermes else "User/Staff"
            dom_history.append(f"[{timestamp}] {sender}: {text}")
        return dom_history
