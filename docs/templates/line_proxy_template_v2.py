import asyncio
import os
import json
import time
import requests
from playwright.async_api import async_playwright

# 1. Configuration & Persistence
STATE_FILE = "/tmp/line_proxy_state.json"
def load_state(target_info):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f: return json.load(f)
    return {"history": [], "target": target_info, "last_msg": None, "active": True}

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, ensure_ascii=False)

# 2. Gemini API Integration (MANDATORY for every turn)
def get_api_key():
    with open(os.path.expanduser("~/.hermes/.env"), "r") as f:
        for line in f:
            if line.startswith("GOOGLE_API_KEY="): return line.split("=", 1)[1].strip()
    return None

async def get_reply(history, system_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={get_api_key()}"
    prompt = f"{system_prompt}\n\nHistory:\n" + "\n".join([f"{m['role']}: {m['text']}" for m in history])
    response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
    return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()

# 3. Main Loop
async def run_proxy(target_contact, system_prompt):
    state = load_state(target_contact)
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        page = next(p for p in browser.contexts[0].pages if "index.html" in p.url)
        input_area = await page.wait_for_selector('div[contenteditable="true"]')

        while state["active"]:
            msgs = await page.evaluate("() => Array.from(document.querySelectorAll('span[data-message-content]')).map(el => el.innerText.trim())")
            if msgs and msgs[0] != state["last_msg"]:
                if msgs[0] in [h['text'] for h in state['history'] if h['role'] == "Hermes"]:
                    state["last_msg"] = msgs[0]; continue
                
                state["history"].append({"role": "Human", "text": msgs[0]})
                reply = await get_reply(state["history"], system_prompt)
                
                await input_area.click()
                await page.keyboard.type(reply)
                await page.keyboard.press("Enter")
                
                state["history"].append({"role": "Hermes", "text": reply})
                state["last_msg"] = reply
                save_state(state)
                
                # Check for closure OR 5-min patience window logic here...
            await asyncio.sleep(5)
