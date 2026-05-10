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
                f"## 任務背景 ##\n"
                f"你是 Hermes，俊羽 的 AI 代理人。你的目標是代表 俊羽 完成以下任務：\n"
                f"任務內容：{self.task_description}\n\n"
                f"## 互動規範 ##\n"
                f"{intro_instruction}\n"
                f"- **身分標籤**：系統會自動處理前綴，回覆內容嚴禁包含 [Hermes] 或類似身分標記。\n"
                f"- **真實性**：僅依據現有的對話歷史進行回覆，嚴禁虛構內容。\n"
                f"- **效率與去重**：嚴禁重複詢問歷史對話中已解決的事項。若對方重複詢問，請精簡、聚焦地回答。\n"
                f"- **退場邏輯**：當任務達成且對方已確認（如：『好的』、『了解』），或雙方已正式完成道別，應立即停止發送訊息並使用相應標籤。\n\n"
                f"{self.etiquette}\n\n"
                f"## 核心執行邏輯 (Hard Rules) ##\n"
                f"1. **禁止擅自決定 (No Unauthorized Pivots)**：若目標時段無法預定或指令僅包含『詢問』，嚴禁擅自答應替代方案。此時應輸出 `[AGENT_INPUT_NEEDED]`。\n"
                f"2. **禁止一次性完成任務**：採取循序漸進策略，每則訊息僅推進一個最優先目標。\n"
                f"3. **優先序**：日期時間 > 人數 > 特殊需求(餐具/停車) > 個人聯絡資訊。\n"
                f"4. **簡潔度**：回覆字數嚴禁超過 40 字，且最多包含一個問句。\n"
                f"\n## 狀態標籤系統 ##\n"
                f"請在訊息末端加上一個合適的標籤：\n"
                f"- `[WAIT_FOR_USER_INPUT]`：已發出詢問，等待對方回覆。\n"
                f"- `[AGENT_INPUT_NEEDED, reason=\"...\"]`：關鍵資訊缺失、任務受阻或目標不合，需要人工介入。\n"
                f"- `[IMPLICIT_ENDED, reason=\"...\"]`：任務達成且對方已確認，無需再回覆。\n"
                f"- `[EXPLICIT_ENDED]`：雙方已完成正式道別。\n"
                f"\n## 對話上下文 ##\n" + "\n".join(context_lines) +
                f"\n\n請根據上述規則與上下文給出回覆："
            )
            
            # SDK generate_content is synchronous
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            full_text = str(getattr(response, 'text', '')).strip()
            
            # Tag Parsing
            waiting_match = "[WAIT_FOR_USER_INPUT]" in full_text
            agent_input_match = re.search(r'\[AGENT_INPUT_NEEDED,\s*reason="([^"]+)"\]', full_text)
            implicit_match = re.search(r'\[IMPLICIT_ENDED,\s*reason="([^"]+)"\]', full_text)
            explicit_match = "[EXPLICIT_ENDED]" in full_text
            
            reply_text = full_text
            # Remove all tags from reply text
            reply_text = re.sub(r'\[AGENT_INPUT_NEEDED,.*?\]', '', reply_text)
            reply_text = re.sub(r'\[IMPLICIT_ENDED,.*?\]', '', reply_text)
            reply_text = reply_text.replace("[WAIT_FOR_USER_INPUT]", "")
            reply_text = reply_text.replace("[EXPLICIT_ENDED]", "").strip()

            if waiting_match:
                self.history.write_log("DEBUG: [WAIT_FOR_USER_INPUT] detected. Waiting for store response.")

            reply_text = re.sub(r'^社交回覆：\s*', '', reply_text)
            
            if reply_text and len(reply_text) > 0:
                if reply_text not in self.state["sent_messages"]:
                    await line_utils.send_message(self.page, reply_text)
                    self.history.write_log(f"SENT: {reply_text}")
                    self.state["sent_messages"].append(reply_text.strip())
            
            # Handle Exit Wait Times
            if agent_input_match:
                reason = agent_input_match.group(1)
                self.state["exit_at"] = time.time() + 120
                self.state["final_report"] = f"AGENT_INPUT_NEEDED: {reason}"
                self.history.write_log(f"Exit Triggered: Agent input needed for '{reason}'. Waiting 120s.")
            elif implicit_match:
                reason = implicit_match.group(1)
                self.state["exit_at"] = time.time() + 300
                self.state["final_report"] = f"IMPLICIT_ENDED: {reason}"
                self.history.write_log(f"Exit Triggered: IMPLICIT_ENDED for '{reason}'. Waiting 300s.")
            elif explicit_match:
                self.state["exit_at"] = time.time() + 120
                self.state["final_report"] = "Conversation explicitly ended."
                self.history.write_log("Exit Triggered: EXPLICIT_ENDED. Waiting 120s.")
            
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
