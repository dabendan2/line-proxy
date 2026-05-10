import asyncio
import os
import json
import time
import requests
from playwright.async_api import async_playwright

# ---------------------------------------------------------
# PERSISTENT NEGOTIATION MONITOR TEMPLATE (HERMES V6+)
# Supports: Crash recovery, Identity defense, Logical pacing
# ---------------------------------------------------------

STATE_FILE = "/tmp/hermes_agent_state.json"
LOG_FILE = "/tmp/hermes_agent.log"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(msg)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return None

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_api_key():
    with open(os.path.expanduser("~/.hermes/.env"), "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("GOOGLE_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1]
    return None

# Context Anchor: Crucial to prevent hallucinations during turns
SYSTEM_PROMPT = """你目前是 Hermes，俊羽 (Chunyu) 的 AI 代理人。
【核心任務資訊 - 不可更改】
- 目標：[如：預約 5/9 13:00 2位大人]
- 姓名：俊羽 / 電話：0912345678

【對話準則】
1. 循序漸進：不要一次丟出大量訊息。先確認核心目標，再處理細節。
2. 防禦性回覆：若被問及未知偏好，必須回覆「我需要跟俊羽確認一下」，不可擅自假設。
3. 邏輯解耦：禁止在同一個訊息中「詢問問題」又「宣告離開去確認」。
"""

async def get_ai_reply(history):
    key = get_api_key()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={key}"
    full_prompt = SYSTEM_PROMPT + "\n\n對話歷史：\n"
    for m in history:
        full_prompt += f"{m['role']}: {m['text']}\n"
    
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    try:
        r = requests.post(url, json=payload).json()
        return r['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        return "ERROR: AI_TIMEOUT"

async def main():
    state = load_state() or {"target": "...", "history": [], "sent_by_me": []}
    log("Agent Resumed" if load_state() else "Agent Started")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        page = [p for p in browser.contexts[0].pages if "index.html" in p.url][0]
        
        last_action_time = time.time()
        is_done = False
        is_consulting = False

        while True:
            # Index 0 is newest
            messages = await page.evaluate("() => Array.from(document.querySelectorAll('.message_text')).map(el => el.innerText.trim())")
            
            if messages:
                latest = messages[0]
                # Identity check: Ignore echoes of what the agent sent
                if latest not in state["sent_by_me"] and (not state["history"] or latest != state["history"][-1]["text"]):
                    log(f"New Input: {latest}")
                    state["history"].append({"role": "User", "text": latest})
                    
                    reply = await get_ai_reply(state["history"])
                    log(f"Hermes: {reply}")
                    
                    await page.type('div[contenteditable="true"]', reply)
                    await page.keyboard.press("Enter")
                    
                    state["history"].append({"role": "Hermes", "text": reply})
                    state["sent_by_me"].append(reply)
                    save_state(state)
                    
                    last_action_time = time.time()
                    
                    # Exit Logic 1: Consulting (2-min buffer)
                    if "確認一下" in reply: is_consulting = True
                    
                    # Exit Logic 2: Completed (5-min buffer)
                    if "完成" in reply or "成功" in reply: is_done = True

            # Timed Exit checks
            now = time.time()
            if is_consulting and now - last_action_time > 120: break
            if is_done and now - last_action_time > 300: break
            
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
