import os
import re
import time
from datetime import datetime

class HistoryManager:
    def __init__(self, chat_name, last_ignored_msg=None, last_ignored_time=None):
        log_dir = os.path.expanduser("~/.line-proxy/logs")
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, f"{chat_name}.log")
        self.last_ignored_msg = last_ignored_msg
        self.last_ignored_time = last_ignored_time

    def write_log(self, msg):
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{t}] {msg}", flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{t}] {msg}\n")

    def get_trusted_history(self):
        trusted = []
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if " SENT: " in line:
                        trusted.append({"text": line.split(" SENT: ", 1)[1].strip(), "sender": "Hermes (AI Proxy)"})
                    elif " NEW MSG: " in line:
                        content = line.split(" NEW MSG: ", 1)[1].strip()
                        text = content.rsplit(" at ", 1)[0] if " at " in content else content
                        trusted.append({"text": text, "sender": "User/Staff"})
        return trusted

    def rebuild_state(self, msgs, task_description):
        trusted_log = []
        last_log_time = None
        
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    timestamp_match = re.match(r"\[(.*?)\]", line)
                    if not timestamp_match: continue
                    
                    t_str = timestamp_match.group(1)
                    try:
                        last_log_time = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").timestamp()
                    except:
                        pass

                    if " SENT: " in line:
                        text = line.split(" SENT: ", 1)[1].strip()
                        trusted_log.append({"text": text, "is_self": True, "time_abs": last_log_time})
                    elif " NEW MSG: " in line:
                        content = line.split(" NEW MSG: ", 1)[1].strip()
                        text = content.rsplit(" at ", 1)[0] if " at " in content else content
                        trusted_log.append({"text": text, "is_self": False, "time_abs": last_log_time})

        sent_messages = [m["text"].strip() for m in trusted_log if m["is_self"]]
        for m in reversed(msgs[:30]):
            if m["is_self_dom"] and m["text"].strip() not in sent_messages:
                sent_messages.append(m["text"].strip())

        state = {
            "last_processed_msg": "",
            "sent_messages": sent_messages,
            "exit_at": None,
            "startup_action_needed": False
        }

        if trusted_log:
            last_entry = trusted_log[-1]
            if last_entry["is_self"]:
                last_new_msg = next((m for m in reversed(trusted_log) if not m["is_self"]), None)
                if last_new_msg:
                    state["last_processed_msg"] = last_new_msg["text"]
                state["startup_action_needed"] = False
                
                # Note: exit_at logic moved to tag-based system in engine.py
            else:
                state["startup_action_needed"] = True
                state["last_processed_msg"] = "___RESTART_RECOVERY___"
        # First run: Use DOM to decide if we need to jump in immediately
        if msgs:
            latest = msgs[0]
            is_hermes = latest.get("has_hermes_prefix", False) or latest.get("is_self_dom", False)
            
            if not is_hermes:
                state["startup_action_needed"] = True
                state["last_processed_msg"] = "___FRESH_TAKEOVER___"
            else:
                state["startup_action_needed"] = False
                state["last_processed_msg"] = latest["text"]
        else:
            state["startup_action_needed"] = ("啟動" in task_description or "開始" in task_description)

        return state

    def get_full_context(self, msgs, sent_messages):
        # We NO LONGER append log content to the context to avoid duplication.
        # We rely solely on the DOM for conversation history, which is the most accurate
        # representation of what the user sees.
        
        dom_history = []
        found_start = False if self.last_ignored_msg else True
        hermes_prefix = "[Hermes]"
        
        for m in reversed(msgs[:50]):
            raw_text = m["text"].strip()
            # Normalize text for boundary comparison
            clean_text = raw_text.replace(hermes_prefix, "").strip()

            if not found_start:
                if clean_text == self.last_ignored_msg.strip():
                    found_start = True
                continue
            
            # Determine sender based on the prefix we physically injected into the DOM
            is_hermes = m.get("has_hermes_prefix", False) or (raw_text.startswith(hermes_prefix))
            sender = "Hermes (AI Proxy)" if is_hermes else "User/Staff"
            
            dom_history.append(f"{sender}: {clean_text}")

        return dom_history
