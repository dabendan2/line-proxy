
import asyncio
import os
import sys
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.abspath("src"))
from channels.factory import ChannelFactory
from utils.config import CDP_PORT, OWNER_NAME

async def check():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
            context = browser.contexts[0]
            from channels.line import driver as line_utils
            page = await line_utils.get_line_page(context)
            
            channel = ChannelFactory.create_instance("line", page=page, owner_name=OWNER_NAME)
            await channel.select_chat("dabendan.test")
            msgs = await channel.extract_messages()
            if msgs:
                print("--- LATEST MESSAGES ---")
                for m in msgs[-8:]:
                    print(f"[{m.get('sender')}]: {m.get('text')}")
            else:
                print("No messages found.")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(check())
