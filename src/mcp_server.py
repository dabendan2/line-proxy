import asyncio
import os
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from browser_manager import BrowserManager
from engine import LineProxyEngine
import line_utils
from playwright.async_api import async_playwright
from lock_manager import PIDLock
from config import CDP_PORT, DEFAULT_PROFILE, DEFAULT_MODEL, LOG_DIR, SCREENSHOT_DIR, \
    ENV_PATH, VIEWPORT_WIDTH, VIEWPORT_HEIGHT, SEARCH_INPUT_SELECTOR, SEARCH_TIMEOUT

# Load .env
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

# Create the MCP server
mcp = FastMCP("LINE Proxy Server")

async def get_page(port):
    """Helper to connect to browser and get LINE page."""
    try:
        browser = await async_playwright().start()
        cdp_browser = await browser.chromium.connect_over_cdp(f"http://localhost:{port}")
        context = cdp_browser.contexts[0]
        page = await line_utils.get_line_page(context)
        return browser, cdp_browser, page
    except Exception as e:
        return None, None, str(e)

@mcp.tool()
async def prepare_line_instance(port: int = CDP_PORT, profile_name: str = DEFAULT_PROFILE):
    """
    Ensures a clean LINE Chromium instance is running on the specified port.
    Handles singleton locks and waits for readiness.
    """
    bm = BrowserManager(port=port, profile_name=profile_name)
    result = bm.prepare_instance()
    return json.dumps(result)

@mcp.tool()
async def find_chat(chat_name: str, port: int = CDP_PORT):
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
            await page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})

            # 1. Search for contact
            await page.wait_for_selector(SEARCH_INPUT_SELECTOR, timeout=SEARCH_TIMEOUT)
            await page.click(SEARCH_INPUT_SELECTOR)
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await page.type(SEARCH_INPUT_SELECTOR, chat_name)
            await asyncio.sleep(2)

            # 2. Use find_line_contact logic (Shadow DOM aware)
            script_path = os.path.join(os.path.dirname(__file__), "find_line_contact.js")
            with open(script_path, "r") as f:
                js_code = f.read()

            status = await page.evaluate(js_code, chat_name)
            
            await asyncio.sleep(2)
            screenshot_path = SCREENSHOT_DIR / f"last_find_{chat_name}.png"
            await page.screenshot(path=screenshot_path)
            
            return json.dumps({
                "status": "success" if status != "not_found" else "not_found",
                "detail": status,
                "screenshot": str(screenshot_path)
            })
        except Exception as e:
            return f"Error: {str(e)}"

@mcp.tool()
async def send_line_message(chat_name: str, text: str, port: int = CDP_PORT):
    """
    Directly sends a message to the specified chat. 
    Assumes the chat is already selected or can be found.
    Adds the standard [Hermes] prefix.
    """
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            
            if not page:
                return "Error: LINE extension page not found."

            await page.bring_to_front()
            
            # Select chat
            selection = await line_utils.select_chat(page, chat_name)
            if selection["status"] not in ["success"]:
                return json.dumps(selection)

            # Send message
            await line_utils.send_message(page, text)
            
            return json.dumps({
                "status": "success",
                "chat": chat_name,
                "text": text
            })
        except Exception as e:
            return f"Error: {str(e)}"

@mcp.tool()
async def get_line_messages(chat_name: str, limit: int = 10, port: int = CDP_PORT):
    """
    Retrieves the most recent N messages from the specified chat.
    Returns a list of objects with text, sender (is_self), and timestamp.
    """
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            
            if not page:
                return "Error: LINE extension page not found."

            await page.bring_to_front()
            
            # Select chat
            selection = await line_utils.select_chat(page, chat_name)
            if selection["status"] not in ["success"]:
                return json.dumps(selection)

            # Extract messages
            messages = await line_utils.extract_messages(page)
            recent = messages[-limit:] if limit > 0 else messages
            
            return json.dumps({
                "status": "success",
                "chat": chat_name,
                "count": len(recent),
                "messages": recent
            })
        except Exception as e:
            return f"Error: {str(e)}"

@mcp.tool()
async def run_task(chat_name: str, task: str, port: int = CDP_PORT, model: str = DEFAULT_MODEL):
    """
    Runs an AI proxy task synchronously for a specific chat.
    This tool blocks until the task is completed or an error occurs.
    Use Hermes' terminal(background=true, notify_on_complete=true) to run this 
    if you need non-blocking behavior with completion notifications.
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not found."

    venv_python = "/home/ubuntu/line-proxy/venv/bin/python3"
    run_script = os.path.join(os.path.dirname(__file__), "run_engine.py")

    cmd = [
        venv_python, run_script,
        "--chat_name", chat_name,
        "--task", task,
        "--port", str(port),
        "--model", model
    ]

    try:
        # Run synchronously using subprocess.run
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        return json.dumps({
            "status": "completed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except Exception as e:
        lock.release()
        return f"Error running task: {str(e)}"

if __name__ == "__main__":
    mcp.run()
