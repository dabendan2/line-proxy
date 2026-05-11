import asyncio
import os
import time
import re
import httpx
from google import genai
import line_utils
from history_manager import HistoryManager
from config import DEFAULT_MODEL, INTRO_PHRASE, HERMES_PREFIX, AGENT_INPUT_WAIT, \
    IMPLICIT_END_WAIT, EXPLICIT_END_WAIT, POLL_INTERVAL, RUNTIME_TIMEOUT, TOOL_WAIT, \
    HERMES_API_URL

class LineProxyEngine:
    def __init__(self, page, chat_name, task, model_name=DEFAULT_MODEL, api_key=None):
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

    def _build_prompt(self, context_lines):
        intro_already_done = any("Hermes" in line and ("AI代理" in line or "AI 代理" in line or "AI Proxy" in line) 
                                 for line in context_lines)
        
        intro_instruction = ("你已經在之前的對話中自我介紹過了，現在請直接針對對方的最新訊息進行回覆，嚴禁再次重複自我介紹。" 
                             if intro_already_done else 
                             f"這是你與對方的第一次對話。請務必先進行自我介紹，開場白應固定為：『{INTRO_PHRASE}』隨後緊接著你的任務內容。")
        
        return (
            f"## 任務背景 ##\n"
            f"你是 Hermes，俊羽 的 AI 代理人。你的目標是代表 俊羽 完成以下任務：\n"
            f"任務內容：{self.task_description}\n\n"
            f"## 互動規範 ##\n"
            f"{intro_instruction}\n"
            f"- **身分標籤**：系統會自動處理前綴，回覆內容嚴禁包含 {HERMES_PREFIX} 或類似身分標記。\n"
            f"- **真實性**：僅依據現有的對話歷史進行回覆，嚴禁虛構內容。\n"
            f"- **效率與去重**：嚴禁重複詢問歷史對話中已解決的事項。若對方重複詢問，請精簡、聚焦地回答。\n"
            f"- **退場邏輯**：當任務達成且對方已確認（如：『好的』、『了解』、『沒問題』、『確認了』），或雙方已正式完成道別，應先禮貌地回應（如：『謝謝您』、『辛苦了』），隨後停止發送訊息並使用相應標籤。如果對方的回覆已經包含了你任務所要求的確認，嚴禁再次詢問。\n"
            f"    - *範例*：對方說『訂好了』 -> 回覆『謝謝您的協助！』並輸出 `[IMPLICIT_ENDED, reason=\"對方已確認完成\"]`。\n"
            f"    - *範例*：對方說『再見』 -> 回覆『好的，再見！』並輸出 `[EXPLICIT_ENDED]`。\n\n"
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
            f"- `[TOOL_ACCESS_NEEDED, tool=\"...\", query=\"...\"]`：為了完成**主任務**，需要存取外部工具（如 `web_search`, `google_drive`）。\n"
            f"    - **限制**：僅在工具為完成「任務內容」所必須，且對話中提及時使用。\n"
            f"    - **嚴禁**：嚴禁為了解決使用者提出的「與主任務無關」的要求（如：玩遊戲時詢問天氣）而使用此標籤。對於無關要求，請禮貌地拒絕或導回主任務。\n"
            f"\n## 對話上下文 ##\n" + "\n".join(context_lines) +
            f"\n\n請根據上述規則與上下文給出回覆："
        )

    def _parse_response(self, full_text):
        waiting_match = "[WAIT_FOR_USER_INPUT]" in full_text
        agent_input_match = re.search(r'\[AGENT_INPUT_NEEDED,\s*reason="([^"]+)"\]', full_text)
        implicit_match = re.search(r'\[IMPLICIT_ENDED,\s*reason="([^"]+)"\]', full_text)
        explicit_match = "[EXPLICIT_ENDED]" in full_text
        tool_match = re.search(r'\[TOOL_ACCESS_NEEDED,\s*tool="([^"]+)",\s*query="([^"]+)"\]', full_text)
        
        reply_text = full_text
        reply_text = re.sub(r'\[AGENT_INPUT_NEEDED,.*?\]', '', reply_text)
        reply_text = re.sub(r'\[IMPLICIT_ENDED,.*?\]', '', reply_text)
        reply_text = re.sub(r'\[TOOL_ACCESS_NEEDED,.*?\]', '', reply_text)
        reply_text = reply_text.replace("[WAIT_FOR_USER_INPUT]", "")
        reply_text = reply_text.replace("[EXPLICIT_ENDED]", "").strip()
        reply_text = re.sub(r'^社交回覆：\s*', '', reply_text)

        return {
            "text": reply_text,
            "is_waiting": waiting_match,
            "agent_input_needed": agent_input_match.group(1) if agent_input_match else None,
            "implicit_ended": implicit_match.group(1) if implicit_match else None,
            "explicit_ended": explicit_match,
            "tool_needed": {"tool": tool_match.group(1), "query": tool_match.group(2)} if tool_match else None
        }

    async def execute_hermes_tool(self, tool_name, query):
        url = f"{HERMES_API_URL}/v1/chat/completions"
        payload = {
            "model": "hermes-agent",
            "messages": [
                {"role": "user", "content": f"Please execute the tool '{tool_name}' for this query: '{query}'. Return only the result."}
            ],
            "stream": False
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def generate_and_send_reply(self, msgs):
        try:
            context_lines = self.history.get_full_context(msgs, self.state["sent_messages"])
            prompt = self._build_prompt(context_lines)
            
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            result = self._parse_response(str(getattr(response, 'text', '')).strip())
            
            if result["is_waiting"]:
                self.history.write_log("DEBUG: [WAIT_FOR_USER_INPUT] detected. Waiting for store response.")
            
            if result["text"] and result["text"] not in self.state["sent_messages"]:
                await line_utils.send_message(self.page, result["text"])
                self.history.write_log(f"SENT: {result['text']}")
                self.state["sent_messages"].append(result["text"].strip())
            
            if result["agent_input_needed"]:
                self.state.update({
                    "exit_at": time.time() + AGENT_INPUT_WAIT,
                    "final_report": f"AGENT_INPUT_NEEDED: {result['agent_input_needed']}"
                })
                self.history.write_log(f"Exit Triggered: AGENT_INPUT_NEEDED for '{result['agent_input_needed']}'.")
            elif result["implicit_ended"]:
                self.state.update({
                    "exit_at": time.time() + IMPLICIT_END_WAIT,
                    "final_report": f"IMPLICIT_ENDED: {result['implicit_ended']}"
                })
                self.history.write_log(f"Exit Triggered: IMPLICIT_ENDED for '{result['implicit_ended']}'.")
            elif result["explicit_ended"]:
                self.state.update({
                    "exit_at": time.time() + EXPLICIT_END_WAIT,
                    "final_report": "Conversation explicitly ended."
                })
                self.history.write_log("Exit Triggered: EXPLICIT_ENDED.")
            elif result["tool_needed"]:
                await line_utils.send_message(self.page, f"[系統] 正在執行工具: {result['tool_needed']['tool']}...")
                try:
                    tool_output = await self.execute_hermes_tool(result['tool_needed']['tool'], result['tool_needed']['query'])
                    self.state["sent_messages"].append(f"[系統通知] 工具執行成功。結果為: {tool_output}")
                    latest = await line_utils.extract_messages(self.page)
                    await self.generate_and_send_reply(latest)
                except Exception as e:
                    error_report = f"[系統錯誤] 工具 {result['tool_needed']['tool']} 執行失敗: {str(e)}"
                    await line_utils.send_message(self.page, error_report)
                
                self.state.update({
                    "exit_at": time.time() + TOOL_WAIT,
                    "final_report": f"TOOL_ACCESS_NEEDED: {result['tool_needed']['tool']}"
                })
            
            latest_msgs = await line_utils.extract_messages(self.page)
            if latest_msgs:
                self.state["last_processed_msg"] = latest_msgs[-1].get("text", "")
                
        except Exception as e:
            self.history.write_log(f"Error in generate_and_send_reply: {e}")

    async def run(self):
        start_time = time.time()
        self.history.write_log(f"Proxy Engine started for {self.target_chat}")
        await self.page.bring_to_front()
        await line_utils.select_chat(self.page, self.target_chat)
        
        msgs = await line_utils.extract_messages(self.page)
        if not msgs: return

        self.state.update(self.history.rebuild_state(msgs, self.task_description))
        await self.generate_and_send_reply(msgs)

        while True:
            if time.time() - start_time > RUNTIME_TIMEOUT:
                timeout_msg = "[RESTART_REQUIRED] Runtime limit reached."
                self.state["final_report"] = timeout_msg
                break
            if self.state.get("exit_at") and time.time() >= self.state["exit_at"]:
                break
            msgs = await line_utils.extract_messages(self.page)
            if msgs:
                latest = msgs[-1]
                is_hermes = latest.get("has_hermes_prefix", False) or latest.get("is_self_dom", False)
                is_new = latest["text"].strip() != self.state.get("last_processed_msg", "").strip()
                if not is_hermes and is_new:
                    if self.state.get("exit_at"): self.state["exit_at"] = None
                    await self.generate_and_send_reply(msgs)
            await asyncio.sleep(POLL_INTERVAL)
