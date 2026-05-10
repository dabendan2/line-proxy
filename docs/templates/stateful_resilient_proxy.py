import asyncio
import json
import os
import time
from playwright.async_api import async_playwright
import google.generativeai as genai

# This template implements the Resilient Intelligent Proxy pattern for LINE
# It uses Gemini Pro to handle conversation context and manages state for crash recovery.

TARGET_CHAT = "TARGET_NAME"
MODEL_NAME = "gemini-3-pro-preview" 
STATE_FILE = f"/tmp/hermes_proxy_{TARGET_CHAT}.json"

# System Prompt defines the goal and social rules
SYSTEM_PROMPT = """
You are Hermes, an AI agent for Chunyu. 
Goal: [Define Goal Here]
Social Rules:
- Incremental Disclosure: One topic per message.
- Human-Led: Answer their questions first.
- Natural Tone: Use Traditional Chinese, be polite and concise.
"""

async def get_latest_messages(page):
    # Extracts text and identifies if it's from the agent (DOM check)
    script = """
    () => {
        const getDeepText = (el) => {
            let text = "";
            if (el.shadowRoot) text += getDeepText(el.shadowRoot);
            for (const child of el.childNodes) {
                text += child.textContent + " ";
                if (child.nodeType === Node.ELEMENT_NODE) text += getDeepText(child);
            }
            return text.trim();
        };
        const msgElements = document.querySelectorAll('span[data-message-content], .message_text, flex-renderer');
        return Array.from(msgElements).map(el => ({
            text: getDeepText(el),
            is_self_dom: el.closest('.mdNM08MsgSelf') !== null
        })).reverse(); 
    }
    """
    return await page.evaluate(script)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"last_processed_msg": "", "exit_at": None, "sent_messages": []}

async def main():
    state = load_state()
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = next(p for p in context.pages if "ophjlpahpchlmihnnnihgmmeilfjmjjc" in p.url)
        
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model = genai.GenerativeModel(MODEL_NAME)

        while True:
            # Handle Exit Timers
            if state.get("exit_at") and time.time() >= state["exit_at"]:
                break
            
            messages = await get_latest_messages(page)
            if not messages:
                await asyncio.sleep(5); continue
            
            # Robust Sender ID (DOM + History Matching)
            processed = [{"text": m["text"], "is_self": m["is_self_dom"] or m["text"] in state["sent_messages"]} for m in messages]
            latest = processed[-1]
            
            if not latest["is_self"] and latest["text"] != state["last_processed_msg"]:
                # New Incoming Message Detected
                state["exit_at"] = None
                history = "\n".join([f"{'Hermes' if m['is_self'] else 'User'}: {m['text']}" for m in processed[-15:]])
                
                response = model.generate_content(f"{SYSTEM_PROMPT}\n\nHistory:\n{history}\n\nReply:")
                reply = response.text.strip()
                
                # Send Reply
                input_area = page.locator('.message_input, [contenteditable="true"], textarea').first
                await input_area.fill(reply)
                await page.keyboard.press("Enter")
                
                state["last_processed_msg"] = latest["text"]
                state["sent_messages"].append(reply)
                
                # Logic for exit timers (2/5/2 rule)
                if "跟俊羽確認" in reply: state["exit_at"] = time.time() + 120
                elif "再見" in reply or "再見" in latest["text"]: state["exit_at"] = time.time() + 120
                elif "好了" in latest["text"]: state["exit_at"] = time.time() + 300
                
                with open(STATE_FILE, "w") as f: json.dump(state, f)
            
            await asyncio.sleep(5)
