import asyncio
from typing import List, Dict, Optional, Any
import os
import time
import re
import httpx
from google import genai
import line_utils
from history_manager import HistoryManager
from config import DEFAULT_MODEL, OWNER_NAME, INTRO_PHRASE, HERMES_PREFIX, AGENT_INPUT_WAIT, \
    CONVERSATION_END_WAIT, POLL_INTERVAL, RUNTIME_TIMEOUT, TOOL_WAIT, \
    HERMES_API_URL

class LineProxyEngine:
    def __init__(self, page: Any, chat_name: str, task: str, chat_id: Optional[str] = None, model_name: str = DEFAULT_MODEL, api_key: Optional[str] = None) -> None:
        self.page = page
        self.target_chat = chat_name
        self.target_chat_id = chat_id
        self.task_description = task
        self.model_name = model_name
        self.history = HistoryManager(chat_name)
        self.client = genai.Client(api_key=api_key)
        
        etiquette_path = os.path.join(os.path.dirname(__file__), "etiquette.md")
        with open(etiquette_path, "r", encoding="utf-8") as f:
            self.etiquette = f.read()

        prompt_path = os.path.join(os.path.dirname(__file__), "engine_prompt.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt_template = f.read()
            
        self.state = {
            "sent_messages": [], 
            "last_processed_msg": "", 
            "exit_at": None, 
            "final_report": None
        }

    def _build_prompt(self, context_lines: List[str]) -> str:
        # TDD FIX: Only consider intro "already done" if it appears in the most recent 10 messages.
        # This ensures that for new sessions or long conversations, the agent re-introduces itself.
        recent_context = context_lines[-10:]
        intro_already_done = any("Hermes" in line and ("AI代理" in line or "AI 代理" in line or "AI Proxy" in line) 
                                 for line in recent_context)
        
        intro_instruction = ("你已經在之前的對話中自我介紹過了，現在請直接針對對方的最新訊息進行回覆，嚴禁再次重複自我介紹。" 
                             if intro_already_done else 
                             f"這是你與對方的第一次對話。請務必先進行自我介紹，開場白應固定為：『{INTRO_PHRASE}』。")
        
        prompt = self.system_prompt_template
        prompt = prompt.replace("{{task_description}}", self.task_description)
        prompt = prompt.replace("{{intro_instruction}}", intro_instruction)
        prompt = prompt.replace("{{HERMES_PREFIX}}", HERMES_PREFIX)
        prompt = prompt.replace("{{etiquette}}", self.etiquette)
        prompt = prompt.replace("{{INTRO_PHRASE}}", INTRO_PHRASE)
        prompt = prompt.replace("{{OWNER_NAME}}", OWNER_NAME)
        prompt = prompt.replace("{{context_lines}}", "\n".join(context_lines))
        
        return prompt

    def _parse_response(self, full_text: str) -> Dict[str, Any]:
        waiting_match = "[WAIT_FOR_USER_INPUT]" in full_text
        agent_input_match = re.search(r'\[AGENT_INPUT_NEEDED,\s*reason="([^"]+)"(?:,\s*summary="([^"]+)")?\]', full_text)
        convo_ended_match = re.search(r'\[CONVERSATION_ENDED,\s*summary="([^"]+)"\]', full_text)
        tool_match = re.search(r'\[TOOL_ACCESS_NEEDED,\s*tool="([^"]+)",\s*query="([^"]+)"\]', full_text)
        
        reply_text = full_text
        reply_text = re.sub(r'\[AGENT_INPUT_NEEDED,.*?\]', '', reply_text)
        reply_text = re.sub(r'\[CONVERSATION_ENDED,.*?\]', '', reply_text)
        reply_text = re.sub(r'\[TOOL_ACCESS_NEEDED,.*?\]', '', reply_text)
        reply_text = reply_text.replace("[WAIT_FOR_USER_INPUT]", "").strip()

        return {
            "text": reply_text,
            "is_waiting": waiting_match,
            "agent_input_needed": agent_input_match.group(1) if agent_input_match else None,
            "summary": (convo_ended_match.group(1) if convo_ended_match else 
                        agent_input_match.group(2) if (agent_input_match and agent_input_match.lastindex >= 2) else None),
            "conversation_ended": convo_ended_match is not None,
            "tool_needed": {"tool": tool_match.group(1), "query": tool_match.group(2)} if tool_match else None
        }

    async def execute_hermes_tool(self, tool_name: str, query: str) -> str:
        toolset_map = {
            "google_drive": "google-workspace",
            "drive": "google-workspace",
            "gmail": "google-workspace",
            "calendar": "google-workspace",
            "web_search": "web",
            "browser": "browser",
            "terminal": "terminal",
            "vision_analyze": "vision",
            "read_file": "file"
        }
        target_toolset = toolset_map.get(tool_name, tool_name)
        
        url = f"{HERMES_API_URL}/v1/chat/completions"
        payload = {
            "model": "hermes-agent",
            "toolsets": [target_toolset],
            "messages": [
                {"role": "system", "content": "You are a minimalist tool executor. Return ONLY raw output."},
                {"role": "user", "content": f"Execute tool '{tool_name}' for query: '{query}'"}
            ],
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def generate_and_send_reply(self, msgs: List[Dict[str, Any]]) -> None:
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
            
            if result["summary"]:
                summary_report = f"\n[REPORT]\n{result['summary']}\n[/REPORT]"
                self.history.write_log(f"--- TASK SUMMARY ---\n{result['summary']}\n--------------------")
                print(summary_report)

            if result["agent_input_needed"]:
                self.state.update({
                    "exit_at": time.time() + AGENT_INPUT_WAIT,
                    "final_report": f"AGENT_INPUT_NEEDED: {result['agent_input_needed']}"
                })
            elif result["conversation_ended"]:
                self.state.update({
                    "exit_at": time.time() + CONVERSATION_END_WAIT,
                    "final_report": "Conversation ended."
                })
            elif result["tool_needed"]:
                await line_utils.send_message(self.page, f"[系統] 正在執行工具: {result['tool_needed']['tool']}...")
                try:
                    tool_output = await self.execute_hermes_tool(result['tool_needed']['tool'], result['tool_needed']['query'])
                    self.state["sent_messages"].append(f"[系統通知] 工具執行成功。結果為: {tool_output}")
                    latest = await line_utils.extract_messages(self.page)
                    await self.generate_and_send_reply(latest)
                except Exception as e:
                    await line_utils.send_message(self.page, f"[系統錯誤] 工具執行失敗: {str(e)}")
                
                self.state.update({
                    "exit_at": time.time() + TOOL_WAIT,
                    "final_report": f"TOOL_ACCESS_NEEDED: {result['tool_needed']['tool']}"
                })
            
            latest_msgs = await line_utils.extract_messages(self.page)
            if latest_msgs:
                self.state["last_processed_msg"] = latest_msgs[-1].get("text", "")
                
        except Exception as e:
            self.history.write_log(f"Error in generate_and_send_reply: {e}")

    async def run(self) -> Optional[str]:
        start_time = time.time()
        self.history.write_log(f"Proxy Engine started for {self.target_chat} (ID: {self.target_chat_id})")
        await self.page.bring_to_front()
        selection = await line_utils.select_chat(self.page, self.target_chat, self.target_chat_id)
        if selection.get("status") != "success":
            error_msg = f"Failed to select chat '{self.target_chat}': {selection.get('error', 'Unknown error')}"
            self.history.write_log(error_msg)
            return error_msg
        
        msgs = await line_utils.extract_messages(self.page)
        # TDD FIX: Proceed even if chat is empty (start of conversation)
        if msgs is None: return

        self.state.update(self.history.rebuild_state(msgs or [], self.task_description))
        await self.generate_and_send_reply(msgs or [])

        while True:
            if time.time() - start_time > RUNTIME_TIMEOUT:
                msg = "[RESTART_REQUIRED] Runtime limit reached."
                self.state["final_report"] = msg
                self.history.write_log(msg)
                break
            if self.state.get("exit_at") and time.time() >= self.state["exit_at"]:
                break
            try:
                msgs = await line_utils.extract_messages(self.page)
                if msgs:
                    latest = msgs[-1]
                    is_hermes = latest.get("sender") in ["Hermes", OWNER_NAME]
                    is_new = latest["text"].strip() != self.state.get("last_processed_msg", "").strip()
                    if not is_hermes and is_new:
                        if self.state.get("exit_at"): self.state["exit_at"] = None
                        await self.generate_and_send_reply(msgs)
            except Exception as e:
                error_msg = f"Critical error in message polling: {e}"
                self.history.write_log(error_msg)
                self.state["final_report"] = error_msg
                break
            await asyncio.sleep(POLL_INTERVAL)

        self.history.write_log("Session concluded.")
        return self.state.get("final_report")
