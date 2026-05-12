import time
from typing import List, Dict, Any
from config import LOG_DIR, OWNER_NAME

class HistoryManager:
    def __init__(self, chat_name: str) -> None:
        self.log_path = LOG_DIR / f"{chat_name}.log"

    def write_log(self, text: str) -> None:
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{t}] {text}", flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{t}] {text}\n")

    def rebuild_state(self, msgs: List[Dict[str, Any]], task_description: str) -> Dict[str, Any]:
        sent_messages = []
        
        if self.log_path.exists():
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if " SENT: " in line:
                        text = line.split(" SENT: ", 1)[1].strip()
                        sent_messages.append(text)

        for m in msgs:
            text = m["text"].strip()
            if m.get("sender") in ["Hermes", OWNER_NAME] and text not in sent_messages:
                sent_messages.append(text)

        state = {
            "last_processed_msg": "",
            "sent_messages": sent_messages,
            "exit_at": None,
            "startup_action_needed": False
        }

        if msgs:
            latest = msgs[-1]
            is_hermes = latest.get("sender") in ["Hermes", OWNER_NAME]
            
            if not is_hermes:
                state["startup_action_needed"] = True
                state["last_processed_msg"] = "___TAKEOVER___"
            else:
                state["startup_action_needed"] = False
                state["last_processed_msg"] = latest["text"]
        else:
            state["startup_action_needed"] = True

        return state

    def get_full_context(self, msgs: List[Dict[str, Any]], sent_messages: List[str]) -> List[str]:
        # Merge DOM messages with internally tracked sent messages (which include tool outputs)
        # to ensure the AI knows what it has already done/discovered.
        context = []
        
        # 1. Start with DOM history
        for m in msgs:
            text = m["text"].strip()
            timestamp = m.get("timestamp", "Unknown Time")
            sender = m.get("sender", "Unknown")
            context.append(f"[{timestamp}] {sender}: {text}")
            
        # 2. Append internally tracked but NOT-YET-SENT status updates (like Tool Results)
        # These are in sent_messages but might not be in the DOM yet or at all.
        for internal_msg in sent_messages:
            if "[系統通知] 工具執行成功" in internal_msg or "[系統通知] 工具執行結果" in internal_msg:
                # Check if this specific result is already reflected in the context
                if internal_msg not in "\n".join(context):
                    context.append(f"[Internal Log] {internal_msg}")
                    
        return context
