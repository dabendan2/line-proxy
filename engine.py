import asyncio
import json
import os
import time
import google.generativeai as genai
from line_utils import extract_messages, send_message

class LineProxyEngine:
    def __init__(self, page, chat_name, task, anchor_text=None, anchor_time=None, model_name="gemini-3-flash-preview", api_key=None):
        self.page = page
        self.target_chat = chat_name
        self.task_description = task
        self.model_name = model_name
        self.anchor_text = anchor_text
        self.anchor_time = anchor_time
        
        self.state_file = f"/tmp/line_proxy_{chat_name}_state.json"
        self.log_path = f"/tmp/line_proxy_{chat_name}.log"
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        etiquette_path = os.path.join(os.path.dirname(__file__), "etiquette.md")
        with open(etiquette_path, "r", encoding="utf-8") as f:
            self.etiquette = f.read()
            
        self.state = self.load_state()

    def log(self, msg):
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{t}] {msg}", flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{t}] {msg}\n")

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {"last_processed_msg": "", "last_processed_time": "", "sent_messages": [], "exit_at": None}

    def save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f)

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

    def rebuild_memory(self, msgs):
        trusted_log = []
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if " SENT: " in line:
                        trusted_log.append({"text": line.split(" SENT: ", 1)[1].strip(), "is_self": True})
                    elif " NEW MSG: " in line:
                        content = line.split(" NEW MSG: ", 1)[1].strip()
                        text = content.rsplit(" at ", 1)[0] if " at " in content else content
                        trusted_log.append({"text": text, "is_self": False})

        # 1. Rebuild our sent messages from log
        self.state["sent_messages"] = [m["text"].strip() for m in trusted_log if m["is_self"]]
        
        # 2. Supplement from DOM (especially for identity tags)
        for m in reversed(msgs[:30]):
            if m["is_self_dom"] and m["text"].strip() not in self.state["sent_messages"]:
                self.state["sent_messages"].append(m["text"].strip())

        # 3. Startup Decision
        latest = msgs[0]
        # If latest is in our 'sent' list (log or DOM), we've already handled it.
        is_hermes_last = latest["text"].strip() in self.state["sent_messages"]
        
        self.state["last_processed_msg"] = latest["text"]
        self.state["last_processed_time"] = latest["time"]

        if is_hermes_last:
            self.log(f"Memory Rebuilt: Hermes spoke last. Status: Waiting.")
            self.state["startup_action_needed"] = False
        else:
            self.log(f"Memory Rebuilt: Other party spoke last. Status: Need to respond.")
            self.state["startup_action_needed"] = True

        # FORCE proactive start for "Start/Initiate" tasks ONLY if we haven't sent anything yet
        if not self.state["sent_messages"] and ("啟動" in self.task_description or "開始" in self.task_description):
            self.log("New 'Start' task detected. Forcing proactive action.")
            self.state["startup_action_needed"] = True
            self.state["exit_at"] = None 

    async def generate_and_send_reply(self, msgs):
        trusted_history = self.get_trusted_history_from_log()
        log_history_texts = [m['text'] for m in trusted_history]
        
        dom_history = []
        found_anchor = False if self.anchor_text else True
        
        for m in reversed(msgs[:50]):
            if not found_anchor:
                if m["text"] == self.anchor_text and (not self.anchor_time or self.anchor_time in m["time"]):
                    found_anchor = True
                else:
                    continue
            
            if m["text"] not in log_history_texts:
                sender = "Hermes (AI Proxy)" if (m["text"].strip() in self.state["sent_messages"]) else "User/Staff"
                dom_history.append(f"{sender}: {m['text']}")

        final_history = dom_history + [f"{m['sender']}: {m['text']}" for m in trusted_history]
        
        prompt = (
            f"## 角色與工作任務 ##\n你現在是 Hermes，代表 Chunyu (賴俊羽) 的 AI 代理人。\n任務：{self.task_description}\n\n"
            f"{self.etiquette}\n\n"
            f"## 對話上下文 (自錨點起) ##\n" + "\n".join(final_history) +
            f"\n\n根據上述歷史與禮儀，請給出下一步回覆（若對話已結案或正在等待，請回報進度）："
        )
        
        try:
            response = self.model.generate_content(prompt)
            reply_text = response.text.strip()
            if reply_text.count('？') > 1 or reply_text.count('?') > 1:
                reply_text = self.model.generate_content(f"縮減為單一回覆：\n{reply_text}").text.strip()
            
            await send_message(self.page, reply_text)
            self.log(f"SENT: {reply_text}")
            
            # Update state after sending
            latest = msgs[0]
            self.state["last_processed_msg"] = latest["text"]
            self.state["last_processed_time"] = latest["time"]
            self.state["sent_messages"].append(reply_text.strip())
            
            if any(kw in reply_text for kw in ["俊羽確認", "委託人確認"]):
                self.state["exit_at"] = time.time() + 120
            elif any(kw in reply_text.lower() for kw in ["再見", "拜拜", "掰掰", "晚點回覆您"]):
                self.state["exit_at"] = time.time() + 120
            
            self.save_state()
        except Exception as e:
            self.log(f"Error in generate_and_send_reply: {e}")

    async def run(self):
        self.log(f"Proxy Engine started for {self.target_chat}")
        await self.page.bring_to_front()
        
        msgs = await extract_messages(self.page)
        if not msgs:
            self.log("No messages found.")
            return

        self.rebuild_memory(msgs)

        # Proactive Start: only if needed and not already hermes
        if self.state.get("startup_action_needed") or "啟動" in self.task_description or "開始" in self.task_description:
            # Re-check if latest is hermes before proactive start to avoid race conditions
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
            is_new = latest["text"] != self.state.get("last_processed_msg") or latest["time"] != self.state.get("last_processed_time")
            
            if not is_hermes and is_new:
                incoming_text = latest["text"]
                incoming_time = latest["time"]
                self.log(f"NEW MSG: {incoming_text} at {incoming_time}")
                self.state["exit_at"] = None
                
                await self.generate_and_send_reply(msgs)

            await asyncio.sleep(5)

        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self.log("Session concluded.")
