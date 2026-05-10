import asyncio
import os
import time
import re
from google import genai
import line_utils
from history_manager import HistoryManager

class LineProxyEngine:
    def __init__(self, page, chat_name, task, model_name="gemini-3-flash-preview", api_key=None):
        self.page = page
        self.target_chat = chat_name
        self.task_description = task
        self.model_name = model_name
        self.history = HistoryManager(chat_name)
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
            
            # Identity Check
            intro_already_done = False
            for line in context_lines:
                if "Hermes" in line and ("AI代理" in line or "AI 代理" in line or "AI Proxy" in line):
                    intro_already_done = True
                    break
            
            intro_instruction = "你已經在之前的對話中自我介紹過了，現在請直接針對對方的最新訊息進行回覆，嚴禁再次重複自我介紹。" if intro_already_done else "這是你與對方的第一次對話。請務必先進行自我介紹，開場白應固定為：『您好，我是 俊羽 的AI代理 Hermes。』隨後緊接著你的任務內容。"

            prompt = (
                f"## 角色與工作任務 ##\n你現在是 Hermes，代表 Chunyu (賴俊羽) 的 AI 代理人。\n"
                f"{intro_instruction}\n"
                f"**重要禁令：嚴禁幻想尚未發生的對話。你只能根據『對話上下文』中確實存在的訊息進行回覆。**\n"
                f"**重要禁令：嚴禁重複詢問或要求對話歷史中已經回答過、或已經解決的事項。**\n"
                f"**溝通準則：若對方詢問了你在歷史對話中已提過的資訊（重複詢問），請「精準、聚焦」地直接回答該問題，不要重複整段預約內容。**\n"
                f"**退場與默契機制：若你的任務目標已達成，且對方的最新回覆是簡短的確認或結束語（例如：『好的』、『了解』、『沒問題』、『知道了』），則嚴禁再發送任何冗餘訊息（如：『再見』、『謝謝』）。請直接輸出 [END] 標籤結束，守候 5 分鐘。**\n"
                f"**退場機制：如果雙方已互道再見，則嚴禁傳送任何新訊息。請直接使用 [END] 標籤結束。**\n"
                f"任務：{self.task_description}\n\n"
                f"{self.etiquette}\n\n"
                f"## 回覆格式規範 ##\n"
                f"1. **社交回覆**：直接寫出要發送給使用者的對話。如果不需要發送訊息，請留空或僅輸出標籤。\n"
                f"2. **終止標籤 (選填)**：若任務已完成、遇到缺失資訊、或已完成道別，請在訊息末端加上：\n"
                f"   `[END, reason=\"(原因)\", report=\"(內部報告內容)\"]` \n"
                f"   - reason 必須是以下之一：\"consulting\", \"accomplished\", \"goodbye\"\n"
                f"\n## 對話上下文 ##\n" + "\n".join(context_lines) +
                f"\n\n根據上述歷史與禮儀，請給出回覆："
            )
            
            # SDK generate_content is synchronous
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            full_text = str(getattr(response, 'text', '')).strip()
            
            tag_match = re.search(r'\[END,\s*reason="([^"]+)",\s*report="([^"]+)"\]', full_text)
            reply_text = full_text
            reason, report = None, ""
            
            if tag_match:
                reason = tag_match.group(1)
                report = tag_match.group(2)
                reply_text = full_text.replace(tag_match.group(0), "").strip()
            
            reply_text = re.sub(r'^社交回覆：\s*', '', reply_text)
            
            if reply_text and len(reply_text) > 0:
                if reply_text not in self.state["sent_messages"]:
                    await line_utils.send_message(self.page, reply_text)
                    self.history.write_log(f"SENT: {reply_text}")
                    self.state["sent_messages"].append(reply_text.strip())
            
            if reason:
                wait_time = 120 if reason != "accomplished" else 300
                self.state["exit_at"] = time.time() + wait_time
                self.state["final_report"] = report
                self.history.write_log(f"Exit Triggered: reason={reason}, waiting {wait_time}s. Report: {report}")
            
            latest_msgs = await line_utils.extract_messages(self.page)
            if latest_msgs and isinstance(latest_msgs, list) and len(latest_msgs) > 0:
                self.state["last_processed_msg"] = latest_msgs[0].get("text", "")
                
        except Exception as e:
            self.history.write_log(f"Error in generate_and_send_reply: {e}")

    async def run(self):
        self.history.write_log(f"Proxy Engine started for {self.target_chat} (using google.genai SDK)")
        await self.page.bring_to_front()
        
        # Ensure correct chat is selected
        selection_result = await line_utils.select_chat(self.page, self.target_chat)
        if selection_result["status"] != "success":
            error_msg = selection_result.get("error", "Unknown selection error")
            self.history.write_log(f"CRITICAL ERROR: {error_msg}")
            
            # If ambiguous, we MUST stop and not send anything
            if selection_result["status"] == "ambiguous":
                self.state["final_report"] = f"Ambiguity Error: {error_msg}"
                return
            
            # For other non-not_found errors, we warn but try to continue
            self.history.write_log(f"Warning: {error_msg}")
            
        msgs = await line_utils.extract_messages(self.page)
        if not msgs: 
            self.history.write_log("No messages extracted. Exiting.")
            return

        self.state.update(self.history.rebuild_state(msgs, self.task_description))
        if self.state.get("startup_action_needed"):
            await self.generate_and_send_reply(msgs)

        while True:
            if self.state.get("exit_at") and time.time() >= self.state["exit_at"]:
                break
            msgs = await line_utils.extract_messages(self.page)
            if not msgs:
                await asyncio.sleep(5); continue
            
            # Since extract_messages now returns Oldest First, 
            # the LATEST message is msgs[-1]
            latest = msgs[-1]
            is_hermes = latest.get("has_hermes_prefix", False) or latest.get("is_self_dom", False)
            is_new = latest["text"].strip() != self.state.get("last_processed_msg", "").strip()
            
            if not is_hermes and is_new:
                if self.state.get("exit_at"): self.state["exit_at"] = None
                await self.generate_and_send_reply(msgs)
            
            await asyncio.sleep(5)
        self.history.write_log("Session concluded.")
