import asyncio
import json
import os
import time
from playwright.async_api import async_playwright
import google.generativeai as genai

# Intelligent Proxy Template v15 (Resilient & Polite)
TARGET_CHAT = "TARGET_NAME"
MODEL_NAME = "gemini-3-flash-preview"
STATE_FILE = f"/tmp/hermes_proxy_{TARGET_CHAT}.json"

SYSTEM_PROMPT = """
你現在是 Chunyu 的 AI 代理人 Hermes。
## 原始需求 (Source of Truth) ##
[貼上原始指令原文]

## 社交規範 ##
1. 循序漸進：一則訊息只處理一件事。
2. 禁止洗畫面：不要重複已發送內容。
3. 人類主導：優先回答對方提問。
"""

async def get_messages(page):
    # Index 0 = Newest message in LINE Extension DOM
    script = """
    () => Array.from(document.querySelectorAll('span[data-message-content], .message_text, flex-renderer')).map(el => ({
        text: el.innerText.trim(),
        is_self_dom: el.closest('.mdNM08MsgSelf') !== null || el.closest('[class*="Self"]') !== null
    }))
    """
    return await page.evaluate(script)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = next(p for p in browser.contexts[0].pages if "ophjlpahpchlmihnnnihgmmeilfjmjjc" in p.url)
        
        # Load known history from DOM to identify Hermes vs Staff
        messages = await get_messages(page)
        sent_messages = [m["text"] for m in messages if m["is_self_dom"]]
        last_processed_msg = ""
        
        # Catch-up logic
        if not (messages[0]["text"] in sent_messages):
            last_processed_msg = messages[1]["text"] if len(messages) > 1 else "BOOT"
        else:
            last_processed_msg = messages[0]["text"]

        exit_at = None
        while True:
            if exit_at and time.time() >= exit_at: break
            
            messages = await get_messages(page)
            latest = messages[0]
            if latest["text"] not in sent_messages and latest["text"] != last_processed_msg:
                # New Reply Detected!
                exit_at = None 
                # [Gemini API Call & Send Message Logic Here]
                # ...
                # last_processed_msg = latest["text"]
                # sent_messages.append(reply)
                # Set exit_at based on reply content (2m/5m)
                pass
            await asyncio.sleep(5)
