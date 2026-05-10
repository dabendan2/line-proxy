import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# 自動載入 ~/.hermes/.env
env_path = Path.home() / ".hermes" / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

import argparse
import os
import sys
from playwright.async_api import async_playwright
from engine import LineProxyEngine
from line_utils import get_line_page
from lock_manager import PIDLock

async def main():
    parser = argparse.ArgumentParser(description="Hermes Generalized LINE Proxy")
    parser.add_argument("--chat", required=True, help="Target contact name")
    parser.add_argument("--task", required=True, help="Detailed task description")
    parser.add_argument("--last-ignored-msg", help="Text of the VERY LAST message to ignore. Context starts AFTER this.")
    parser.add_argument("--last-ignored-time", help="Timestamp of the last ignored message (e.g., '2:19 AM')")
    parser.add_argument("--model", default="gemini-3-flash-preview", help="Gemini model name")
    args = parser.parse_args()

    # 1. Acquire PID Lock to prevent duplicates
    lock = PIDLock(args.chat)
    if not lock.acquire():
        sys.exit(0) # Silent exit if already running

    # Load API Key
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not set.")
        lock.release()
        return

    async with async_playwright() as p:
        try:
            # Connect to existing browser
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            
            page = await get_line_page(context)
            if not page:
                print("Error: LINE page not found.")
                await browser.close()
                lock.release()
                return

            engine = LineProxyEngine(
                page=page,
                chat_name=args.chat,
                task=args.task,
                last_ignored_msg=args.last_ignored_msg,
                last_ignored_time=args.last_ignored_time,
                model_name=args.model,
                api_key=api_key
            )
            
            # Pass lock to engine so it can release on graceful exit
            engine.lock = lock
            await engine.run()
            
            await browser.close()
        except Exception as e:
            print(f"Runtime Error: {e}")
        finally:
            lock.release()

if __name__ == "__main__":
    asyncio.run(main())
