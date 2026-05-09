import os
import re
import time
from datetime import datetime

class HistoryManager:
    def __init__(self, chat_name, last_ignored_msg=None, last_ignored_time=None):
        self.log_path = f"/tmp/line_proxy_{chat_name}.log"
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
                
                reply_text = last_entry["text"]
                if any(kw in reply_text for kw in ["俊羽確認", "委託人確認", "再見", "拜拜", "掰掰", "晚點回覆您"]):
                    state["exit_at"] = last_entry["time_abs"] + 120
                elif any(kw in reply_text for kw in ["預約成功", "好的", "謝謝"]):
                    state["exit_at"] = last_entry["time_abs"] + 300
            else:
                state["startup_action_needed"] = True
                state["last_processed_msg"] = "___RESTART_RECOVERY___"
        else:
            # First run: Use DOM to decide if we need to jump in immediately
            if msgs and not msgs[0]["is_self_dom"]:
                state["startup_action_needed"] = True
                state["last_processed_msg"] = "___FRESH_TAKEOVER___"
            else:
                state["startup_action_needed"] = ("啟動" in task_description or "開始" in task_description)

        return state

    def get_full_context(self, msgs, sent_messages):
        trusted_history = self.get_trusted_history()
        log_history_texts = [m['text'] for m in trusted_history]
        
        dom_history = []
        found_start = False if self.last_ignored_msg else True
        
        for m in reversed(msgs[:50]):
            if not found_start:
                if m["text"] == self.last_ignored_msg and (not self.last_ignored_time or self.last_ignored_time in m["time"]):
                    found_start = True
                else:
                    continue
            
            if m["text"] not in log_history_texts:
                sender = "Hermes (AI Proxy)" if (m["text"].strip() in sent_messages) else "User/Staff"
                dom_history.append(f"{sender}: {m['text']}")

        return dom_history + [f"{m['sender']}: {m['text']}" for m in trusted_history]
