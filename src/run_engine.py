import argparse
import asyncio
import os
import sys
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import line_utils
from engine import LineProxyEngine
from lock_manager import PIDLock
from config import CDP_PORT, DEFAULT_MODEL, ENV_PATH

async def main():
    parser = argparse.ArgumentParser(description="LINE Proxy Engine CLI")
    parser.add_argument("--chat_name", required=True, help="Name of the chat to manage")
    parser.add_argument("--task", required=True, help="Task description for the AI")
    parser.add_argument("--port", type=int, default=CDP_PORT, help="CDP port")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model name")
    args = parser.parse_args()

    # Load .env
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.")
        sys.exit(1)

    # Refactor task using Stepped Communication logic
    from task_refactorer import TaskRefactorer
    refactorer = TaskRefactorer(api_key=api_key, model_name=args.model)
    refactored_task = refactorer.refactor(args.task)
    print(f"DEBUG: Refactored Task:\n{refactored_task}")

    lock = PIDLock(args.chat_name)
    if not lock.acquire():
        print(f"Error: Chat '{args.chat_name}' is already being managed.")
        sys.exit(1)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{args.port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            
            if not page:
                print("Error: LINE page not found.")
                lock.release()
                sys.exit(1)

            engine = LineProxyEngine(
                page=page,
                chat_name=args.chat_name,
                task=refactored_task,
                model_name=args.model,
                api_key=api_key
            )
            engine.lock = lock
            
            await engine.run()
            print(f"Success: Task for '{args.chat_name}' completed.")
        except Exception as e:
            print(f"Error: {str(e)}")
            lock.release()
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
