import asyncio
import json
import os
import time
import google.generativeai as genai
import re
from datetime import datetime
from line_utils import extract_messages, send_message

class LineProxyEngine:
    def __init__(self, page, chat_name, task, last_ignored_msg=None, last_ignored_time=None, model_name="gemini-3-flash-preview", api_key=None):
        self.page = page
        self.target_chat = chat_name
        self.task_description = task
        self.model_name = model_name
        self.last_ignored_msg = last_ignored_msg
        self.last_ignored_time = last_ignored_time
        
        self.log_path = f"/tmp/line_proxy_{chat_name}.log"
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        etiquette_path = os.path.join(os.path.dirname(__file__), "etiquette.md")
        with open(etiquette_path, "r", encoding="utf-8") as f:
            self.etiquette = f.read()
            
        # Operational State (In-Memory Only)
        self.state = {
            "last_processed_msg": "",
            "last_processed_time": "",
            "sent_messages": [],
            "exit_at": None,
            "startup_action_needed": False
        }

    def log(self, msg):
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{t}] {msg}", flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{t}] {msg}\n")

    def get_trusted_history_from_log(self):
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

    def rebuild_memory_and_state(self, msgs):
        """
        Reconstructs the entire operational state from the log file.
        No JSON dependency.
        """
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

        # 1. Rebuild sent_messages (to avoid echoing ourselves)
        self.state["sent_messages"] = [m["text"].strip() for m in trusted_log if m["is_self"]]
        
        # Supplement with DOM (for historical identity check)
        for m in reversed(msgs[:30]):
            if m["is_self_dom"] and m["text"].strip() not in self.state["sent_messages"]:
                self.state["sent_messages"].append(m["text"].strip())

        # 2. Determine last processed message
        # If the last thing in log was a SENT, then the NEW MSG before it is considered 'processed'.
        # If the last thing in log was a NEW MSG, then we have an unprocessed item.
        if trusted_log:
            last_entry = trusted_log[-1]
            if last_entry["is_self"]:
                # We spoke last. Find the NEW MSG that triggered this.
                last_new_msg = next((m for m in reversed(trusted_log) if not m["is_self"]), None)
                if last_new_msg:
                    self.state["last_processed_msg"] = last_new_msg["text"]
                    # We don't have the original LINE timestamp in the log reliably for processed checks,
                    # so we rely on content matching or just being in 'waiting' mode.
                self.log(f"Rebuild: Hermes spoke last ('{last_entry['text'][:30]}...'). Status: Waiting.")
                self.state["startup_action_needed"] = False
                
                # 3. Reconstruct Exit Timer from last SENT content
                reply_text = last_entry["text"]
                if any(kw in reply_text for kw in ["俊羽確認", "委託人確認"]):
                    self.state["exit_at"] = last_entry["time_abs"] + 120
                elif any(kw in reply_text.lower() for kw in ["再見", "拜拜", "掰掰", "晚點回覆您"]):
                    self.state["exit_at"] = last_entry["time_abs"] + 120
                else:
                    # Default finish timer if task seems done
                    if any(kw in reply_text for kw in ["預約成功", "好的", "謝謝"]):
                        self.state["exit_at"] = last_entry["time_abs"] + 300
            else:
                # User spoke last.
                self.log(f"Rebuild: Other party spoke last ('{last_entry['text'][:30]}...'). Status: Need to respond.")
                self.state["startup_action_needed"] = True
                self.state["last_processed_msg"] = "___RESTART_RECOVERY___"
        else:
            # First run
            self.log("Rebuild: No existing log. Fresh start.")
            self.state["startup_action_needed"] = ("啟動" in self.task_description or "開始" in self.task_description)

    async def generate_and_send_reply(self, msgs):
        trusted_history = self.get_trusted_history_from_log()
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
                sender = "Hermes (AI Proxy)" if (m["text"].strip() in self.state["sent_messages"]) else "User/Staff"
                dom_history.append(f"{sender}: {m['text']}")

        final_history = dom_history + [f"{m['sender']}: {m['text']}" for m in trusted_history]
        
        prompt = (
            f"## 角色與工作任務 ##\n你現在是 Hermes，代表 Chunyu (賴俊羽) 的 AI 代理人。\n任務：{self.task_description}\n\n"
            f"{self.etiquette}\n\n"
            f"## 對話上下文 (排除已忽略訊息後) ##\n" + "\n".join(final_history) +
            f"\n\n根據上述歷史與禮儀，請給出下一步回覆（若對話已結案或正在等待，請回報進度）："
        )
        
        try:
            response = self.model.generate_content(prompt)
            reply_text = response.text.strip()
            if reply_text.count('？') > 1 or reply_text.count('?') > 1:
                reply_text = self.model.generate_content(f"縮減為單一回覆：\n{reply_text}").text.strip()
            
            await send_message(self.page, reply_text)
            self.log(f"SENT: {reply_text}")
            
            # Update state
            latest = msgs[0]
            self.state["last_processed_msg"] = latest["text"]
            self.state["last_processed_time"] = latest["time"]
            self.state["sent_messages"].append(reply_text.strip())
            
            # Set exit timer
            now = time.time()
            if any(kw in reply_text for kw in ["俊羽確認", "委託人確認"]):
                self.state["exit_at"] = now + 120
            elif any(kw in reply_text.lower() for kw in ["再見", "拜拜", "掰掰", "晚點回覆您"]):
                self.state["exit_at"] = now + 120
            
        except Exception as e:
            self.log(f"Error in generate_and_send_reply: {e}")

    async def run(self):
        self.log(f"Proxy Engine started for {self.target_chat}")
        await self.page.bring_to_front()
        
        msgs = await extract_messages(self.page)
        if not msgs:
            self.log("No messages found.")
            return

        self.rebuild_memory_and_state(msgs)

        if self.state.get("startup_action_needed"):
            # Final check to avoid race condition
            msgs = await extract_messages(self.page)
            if msgs[0]["text"].strip() not in self.state["sent_messages"]:
                self.log("Proactive Start: Generating initial response...")
                await self.generate_and_send_reply(msgs)

        while True:
            if self.state["exit_at"] and time.time() >= self.state["exit_at"]:
                self.log("Exit timer reached. Task complete.")
                break
            
            msgs = await extract_messages(self.page)
            if not msgs:
                await asyncio.sleep(5)
                continue
            
            latest = msgs[0]
            is_hermes = latest["text"].strip() in self.state["sent_messages"]
            # To be extra safe with content-only matching:
            is_new = latest["text"] != self.state.get("last_processed_msg")
            
            if not is_hermes and is_new:
                incoming_text = latest["text"]
                incoming_time = latest["time"]
                self.log(f"NEW MSG: {incoming_text} at {incoming_time}")
                self.state["exit_at"] = None
                await self.generate_and_send_reply(msgs)

            await asyncio.sleep(5)

        self.log("Session concluded.")
