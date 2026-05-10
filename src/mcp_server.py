import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from browser_manager import BrowserManager
from engine import LineProxyEngine
import line_utils
from playwright.async_api import async_playwright
from lock_manager import PIDLock

# Load .env
env_path = Path.home() / ".hermes" / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Create the MCP server
mcp = FastMCP("LINE Proxy Server")

@mcp.tool()
async def prepare_line_instance(port: int = 9222, profile_name: str = "line_booking_session"):
    """
    Ensures a clean LINE Chromium instance is running on the specified port.
    Handles singleton locks and waits for readiness.
    """
    bm = BrowserManager(port=port, profile_name=profile_name)
    result = bm.prepare_instance()
    return json.dumps(result)

@mcp.tool()
async def find_chat(chat_name: str, port: int = 9222):
    """
    Finds and opens a specific chat window in the LINE extension.
    Shadow-DOM aware and handles profile overlay transitions.
    """
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            
            if not page:
                return "Error: LINE extension page not found."

            await page.bring_to_front()
            await page.set_viewport_size({"width": 1600, "height": 1000})

            # 1. Search for contact
            search_selector = "input[placeholder*='Search'], input[placeholder*='搜尋'], .search_input, input[type='text']"
            await page.wait_for_selector(search_selector, timeout=10000)
            await page.click(search_selector)
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await page.type(search_selector, chat_name)
            await asyncio.sleep(2)

            # 2. Use find_line_contact logic (Shadow DOM aware)
            script_path = os.path.join(os.path.dirname(__file__), "find_line_contact.js")
            with open(script_path, "r") as f:
                js_code = f.read()

            status = await page.evaluate(js_code, chat_name)
            
            await asyncio.sleep(2)
            screenshot_path = f"/home/ubuntu/.line-proxy/last_find_{chat_name}.png"
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            await page.screenshot(path=screenshot_path)
            
            return json.dumps({
                "status": "success" if status != "not_found" else "not_found",
                "detail": status,
                "screenshot": screenshot_path
            })
        except Exception as e:
            return f"Error: {str(e)}"

@mcp.tool()
async def start_proxy_task(chat_name: str, task: str, port: int = 9222, model: str = "gemini-3-flash-preview"):
    """
    Starts the AI proxy engine for a specific chat and task.
    Runs until the task is complete or user input is needed.
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return f"Error: GEMINI_API_KEY not found in environment. ENV keys: {list(os.environ.keys())}"

    lock = PIDLock(chat_name)
    if not lock.acquire():
        return f"Error: Chat '{chat_name}' is already being managed by another process."

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            
            if not page:
                lock.release()
                return "Error: LINE page not found."

            engine = LineProxyEngine(
                page=page,
                chat_name=chat_name,
                task=task,
                model_name=model,
                api_key=api_key
            )
            engine.lock = lock
            
            await engine.run() 
            
            report = engine.state.get("final_report", "Task cycle completed.")
            return json.dumps({
                "status": "completed",
                "report": report
            })
        except Exception as e:
            lock.release()
            return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
