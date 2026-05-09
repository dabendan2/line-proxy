import asyncio
import os
import time
import google.generativeai as genai
from line_utils import extract_messages, send_message
from history_manager import HistoryManager

class LineProxyEngine:
    def __init__(self, page, chat_name, task, last_ignored_msg=None, last_ignored_time=None, model_name="gemini-3-flash-preview", api_key=None):
        self.page = page
        self.target_chat = chat_name
        self.task_description = task
        self.model_name = model_name
        
        self.history = HistoryManager(chat_name, last_ignored_msg, last_ignored_time)
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        etiquette_path = os.path.join(os.path.dirname(__file__), "etiquette.md")
        with open(etiquette_path, "r", encoding="utf-8") as f:
            self.etiquette = f.read()
            
        self.state = {}

    async def generate_and_send_reply(self, msgs):
        context_lines = self.history.get_full_context(msgs, self.state["sent_messages"])
        
        prompt = (
            f"## 角色與工作任務 ##\n你現在是 Hermes，代表 Chunyu (賴俊羽) 的 AI 代理人。\n任務：{self.task_description}\n\n"
            f"{self.etiquette}\n\n"
            f"## 對話上下文 (排除已忽略訊息後) ##\n" + "\n".join(context_lines) +
            f"\n\n根據上述歷史與禮儀，請給出下一步回覆（若對話已結案或正在等待，請回報進度）："
        )
        
        try:
            response = self.model.generate_content(prompt)
            reply_text = response.text.strip()
            if reply_text.count('？') > 1 or reply_text.count('?') > 1:
                reply_text = self.model.generate_content(f"縮減為單一回覆：\n{reply_text}").text.strip()
            
            await send_message(self.page, reply_text)
            self.history.write_log(f"SENT: {reply_text}")
            
            # Update local state
            latest = msgs[0]
            self.state["last_processed_msg"] = latest["text"]
            self.state["sent_messages"].append(reply_text.strip())
            
            now = time.time()
            if any(kw in reply_text for kw in ["俊羽確認", "委託人確認", "再見", "拜拜", "掰掰", "晚點回覆您"]):
                self.state["exit_at"] = now + 120
            
        except Exception as e:
            self.history.write_log(f"Error in generate_and_send_reply: {e}")

    async def run(self):
        self.history.write_log(f"Proxy Engine started for {self.target_chat}")
        await self.page.bring_to_front()
        
        msgs = await extract_messages(self.page)
        if not msgs:
            self.history.write_log("No messages found.")
            return

        self.state = self.history.rebuild_state(msgs, self.task_description)

        if self.state.get("startup_action_needed"):
            msgs = await extract_messages(self.page)
            if msgs[0]["text"].strip() not in self.state["sent_messages"]:
                self.history.write_log("Proactive Start: Generating response...")
                await self.generate_and_send_reply(msgs)

        while True:
            if self.state.get("exit_at") and time.time() >= self.state["exit_at"]:
                self.history.write_log("Exit timer reached. Task complete.")
                break
            
            msgs = await extract_messages(self.page)
            if not msgs:
                await asyncio.sleep(5)
                continue
            
            latest = msgs[0]
            is_hermes = latest["text"].strip() in self.state["sent_messages"]
            is_new = latest["text"] != self.state.get("last_processed_msg")
            
            if not is_hermes and is_new:
                self.history.write_log(f"NEW MSG: {latest['text']} at {latest.get('time', '')}")
                self.state["exit_at"] = None
                await self.generate_and_send_reply(msgs)

            await asyncio.sleep(5)

        self.history.write_log("Session concluded.")
