import asyncio
import os
import json
import time
import requests
from playwright.async_api import async_playwright

# Template for a stateful, persistent negotiation agent (e.g., Hermes Proxy)
# Patterns: State Persistence, Context Anchoring, 1-Minute Safety Window, 
#           Deduplication, and Recursive Shadow DOM extraction.

STATE_FILE = "/tmp/agent_state.json"
LOG_FILE = "/tmp/agent_negotiation.log"

def log(msg):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")

def get_api_key():
    try:
        with open(os.path.expanduser("~/.hermes/.env"), "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GOOGLE_API_KEY=") and not line.startswith("#"):
                    return line.split("=", 1)[1]
    except Exception:
        return None

GOOGLE_API_KEY = get_api_key()
MODEL_NAME = "gemini-flash-latest" 
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}"

# --- ANCHORS: Critical task data that must be in every prompt to prevent hallucination ---
ANCHORS = {
    "goal": "Reserve for 5/9 at 13:00",
    "constraints": "2 Adults, No Kids",
    "knowns": "Name: Junyu, Phone: 0912345678",
    "unknowns": "Parking, Celebration info (Need to ask user if queried)"
}

SYSTEM_PROMPT = f"""你目前是 Hermes，俊羽 (Chunyu) 的 AI 代理人。
你正在進行[任務類型]對話。

任務錨點 (絕對事實)：
- 目標：{ANCHORS['goal']}
- 限制：{ANCHORS['constraints']}
- 已知資訊：{ANCHORS['knowns']}
- 待確認：{ANCHORS['unknowns']}

對話準則：
1. 口吻自然、禮貌。
2. 資訊分段提供，不要一次傾倒。
3. 對於「待確認」資訊，回覆「需跟俊羽確認一下」並維持對話。
4. 偵測到「再見/好的」或任務圓滿完成後 1 分鐘無訊息則關閉。
"""

async def get_ai_response(history):
    url = BASE_URL.format(MODEL_NAME, GOOGLE_API_KEY)
    full_prompt = SYSTEM_PROMPT + "\n\n對話歷史：\n"
    for msg in history:
        full_prompt += f"{msg['role']}: {msg['text']}\n"
    full_prompt += "\n請給出自然回覆："
    
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        return f"Error: {e}"

async def main_loop():
    # Load/Init State
    state = {"history": [], "last_msg": None, "task_done": False}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f: state = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "index.html" in pg.url), None)
        
        input_area = await page.wait_for_selector('div[contenteditable="true"]')
        last_action_time = time.time()

        while True:
            # Recursive Shadow DOM check for Flex Messages
            messages = await page.evaluate("""() => {
                const getDeepText = (el) => {
                    let text = "";
                    if (el.shadowRoot) text += getDeepText(el.shadowRoot);
                    for (const child of el.childNodes) {
                        text += child.textContent + " ";
                        if (child.nodeType === 1) text += getDeepText(child);
                    }
                    return text;
                };
                return Array.from(document.querySelectorAll('span[data-message-content], flex-renderer'))
                    .map(el => el.getAttribute('data-message-content') || getDeepText(el).trim())
                    .filter(t => t.length > 0);
            }""")

            if messages:
                latest = messages[0]
                # New Message Detection & De-duplication
                if latest != state["last_msg"] and latest not in [h['text'] for h in state['history'] if h['role'] == "Hermes"]:
                    log(f"Human: {latest}")
                    state["history"].append({"role": "Human", "text": latest})
                    
                    # Logic
                    reply = await get_ai_response(state["history"])
                    log(f"Hermes: {reply}")
                    
                    await input_area.click()
                    await page.keyboard.type(reply)
                    await page.keyboard.press("Enter")
                    
                    state["history"].append({"role": "Hermes", "text": reply})
                    state["last_msg"] = reply
                    last_action_time = time.time()
                    
                    # State check for completion
                    if "確認成功" in reply or "好的" in latest:
                        state["task_done"] = True
                    
                    # Save State
                    with open(STATE_FILE, "w") as f: json.dump(state, f, ensure_ascii=False)

                    # Immediate exit on goodbye
                    if any(x in latest for x in ["再見", "拜拜"]): break

            # Completion Exit (1-minute window)
            if state["task_done"] and (time.time() - last_action_time > 60):
                log("Task done. Exiting.")
                break
                
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main_loop())
