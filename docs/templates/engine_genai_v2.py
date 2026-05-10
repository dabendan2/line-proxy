import asyncio
import os
import time
import re
from google import genai
import line_utils # Requires extract_messages, send_message
from history_manager import HistoryManager

class LineProxyEngine:
    """
    Generalized AI Proxy Engine for LINE using google-genai (v2 SDK).
    Supports redundancy prevention, consulting protocols, and graceful exits.
    """
    def __init__(self, page, chat_name, task, last_ignored_msg=None, last_ignored_time=None, model_name="gemini-3-flash-preview", api_key=None):
        self.page = page
        self.target_chat = chat_name
        self.task_description = task
        self.model_name = model_name
        self.history = HistoryManager(chat_name, last_ignored_msg, last_ignored_time)
        self.client = genai.Client(api_key=api_key)
        
        etiquette_path = os.path.join(os.path.dirname(__file__), "etiquette.md")
        with open(etiquette_path, "r", encoding="utf-8") as f:
            self.etiquette = f.read()
            
        self.state = {
            "sent_messages": [], 
            "last_processed_msg": "", 
            "exit_at": None, 
            "final_report": None
        }

    async def generate_and_send_reply(self, msgs):
        try:
            context_lines = self.history.get_full_context(msgs, self.state["sent_messages"])
            
            # Identity Check: Prevent redundant intros
            intro_already_done = any("Hermes" in line and ("AI代理" in line or "AI Proxy" in line) for line in context_lines)
            
            intro_instruction = (
                "你已經在之前的對話中自我介紹過了，請直接針對對方的最新訊息進行回覆，嚴禁重複自我介紹。" 
                if intro_already_done else 
                "這是第一次對話。請務必先自我介紹：『您好，我是 俊羽 的AI代理 Hermes。』隨後開始任務。"
            )

            prompt = (
                f"## 角色 ##\n你現在是 Hermes，代表 Chunyu (賴俊羽) 的 AI 代理人。\n{intro_instruction}\n"
                f"**重要禁令**：嚴禁重複詢問歷史對話中已回答或已解決的事項。\n"
                f"**退場機制**：若雙方已互道再見（再見、謝謝）且任務已達成，嚴禁傳訊，僅輸出 [END] 標籤。\n"
                f"任務：{self.task_description}\n\n{self.etiquette}\n\n"
                f"## 對話上下文 ##\n" + "\n".join(context_lines) +
                f"\n\n根據上述歷史與禮儀，請給出回覆（含 [END, reason=\"...\", report=\"...\"] 標籤若適用）："
            )
            
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            full_text = str(getattr(response, 'text', '')).strip()
            
            tag_match = re.search(r'\[END,\s*reason="([^"]+)",\s*report="([^"]+)"\]', full_text)
            reply_text = full_text
            reason = None
            report = ""
            
            if tag_match:
                reason = tag_match.group(1)
                report = tag_match.group(2)
                reply_text = full_text.replace(tag_match.group(0), "").strip()
            
            if reply_text and "MagicMock" not in reply_text:
                if reply_text not in self.state["sent_messages"]:
                    await line_utils.send_message(self.page, reply_text)
                    self.history.write_log(f"SENT: {reply_text}")
                    self.state["sent_messages"].append(reply_text)
            
            if reason:
                wait_time = 300 if reason == "accomplished" else 120
                self.state["exit_at"] = time.time() + wait_time
                self.state["final_report"] = report
                self.history.write_log(f"Exit Triggered: {reason}. Report: {report}")
            
            latest_msgs = await line_utils.extract_messages(self.page)
            if latest_msgs: self.state["last_processed_msg"] = latest_msgs[0].get("text", "")
                
        except Exception as e:
            self.history.write_log(f"Error in generate_and_send_reply: {e}")

    async def run(self):
        self.history.write_log(f"Proxy Engine started for {self.target_chat}")
        await self.page.bring_to_front()
        msgs = await line_utils.extract_messages(self.page)
        if not msgs: return

        self.state.update(self.history.rebuild_state(msgs, self.task_description))
        if self.state.get("startup_action_needed"): await self.generate_and_send_reply(msgs)

        while True:
            if self.state.get("exit_at") and time.time() >= self.state["exit_at"]: break
            msgs = await line_utils.extract_messages(self.page)
            if not msgs: await asyncio.sleep(5); continue
            
            latest = msgs[0]
            is_hermes = latest.get("has_hermes_prefix", False) or latest.get("is_self_dom", False)
            is_new = latest["text"].strip() != self.state.get("last_processed_msg", "").strip()
            
            if not is_hermes and is_new:
                if self.state.get("exit_at"): self.state["exit_at"] = None
                await self.generate_and_send_reply(msgs)
            await asyncio.sleep(5)
        self.history.write_log("Session concluded.")
