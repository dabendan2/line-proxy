import asyncio
import os
from typing import List, Dict, Any, Optional
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
    ENV_PATH, VIEWPORT_WIDTH, VIEWPORT_HEIGHT, SEARCH_INPUT_SELECTOR, SEARCH_TIMEOUT, OWNER_NAME

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

mcp = FastMCP("LINE Proxy Server")

@mcp.tool()
async def prepare_line_instance(port: int = CDP_PORT, profile_name: str = DEFAULT_PROFILE) -> str:
    bm = BrowserManager(port=port, profile_name=profile_name)
    result = bm.prepare_instance()
    return json.dumps(result)

@mcp.tool()
async def find_private_chat(chat_name: str, port: int = CDP_PORT) -> str:
    """Strictly finds and opens a private chat window from the Friends list."""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            if not page: return "Error: LINE extension page not found."
            await page.bring_to_front()
            await page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
            result = await line_utils.find_private_chat(page, chat_name)
            screenshot_path = SCREENSHOT_DIR / f"last_find_{chat_name}.png"
            await page.screenshot(path=screenshot_path)
            result["screenshot"] = str(screenshot_path)
            return json.dumps(result)
        except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
async def send_line_message(chat_name: str, text: str, port: int = CDP_PORT) -> str:
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            if not page: return "Error: LINE extension page not found."
            await page.bring_to_front()
            selection = await line_utils.select_chat(page, chat_name)
            if selection["status"] not in ["success"]: return json.dumps(selection)
            await line_utils.send_message(page, text)
            return json.dumps({"status": "success", "chat": chat_name, "text": text})
        except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
async def get_line_messages(chat_name: str, limit: int = 10, port: int = CDP_PORT) -> str:
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            if not page: return "Error: LINE extension page not found."
            await page.bring_to_front()
            selection = await line_utils.select_chat(page, chat_name)
            if selection["status"] not in ["success"]: return json.dumps(selection)
            messages = await line_utils.extract_messages(page, owner_name=OWNER_NAME, chat_name=chat_name)
            recent = messages[-limit:] if limit > 0 else messages
            return json.dumps({"status": "success", "chat": chat_name, "count": len(recent), "messages": recent})
        except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
async def run_task(chat_name: str, task: str, port: int = CDP_PORT, model: str = DEFAULT_MODEL) -> str:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key: return "Error: GEMINI_API_KEY not found."
    venv_python = "/home/ubuntu/line-proxy/venv/bin/python3"
    run_script = os.path.join(os.path.dirname(__file__), "run_engine.py")
    cmd = [venv_python, run_script, "--chat_name", chat_name, "--task", task, "--port", str(port), "--model", model]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return json.dumps({"status": "completed" if result.returncode == 0 else "failed", "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    except Exception as e: return f"Error running task: {str(e)}"

if __name__ == "__main__":
    mcp.run()
