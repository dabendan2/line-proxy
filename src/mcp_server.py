import os
import sys
from typing import List, Dict, Any, Optional
import json
import subprocess
from mcp.server.fastmcp import FastMCP
from browser_manager import BrowserManager
from engine import LineProxyEngine
import line_utils
from playwright.async_api import async_playwright
from config import CDP_PORT, DEFAULT_PROFILE, DEFAULT_MODEL, LOG_DIR, SCREENSHOT_DIR, \
    ENV_PATH, VIEWPORT_WIDTH, VIEWPORT_HEIGHT, SEARCH_INPUT_SELECTOR, SEARCH_TIMEOUT, OWNER_NAME, \
    LINE_EMAIL, LINE_PASSWORD

mcp = FastMCP("LINE Proxy Server")

@mcp.tool()
async def login_line(port: int = CDP_PORT) -> str:
    """Performs automated login using credentials from .env and returns MFA code if needed."""
    if not LINE_EMAIL or not LINE_PASSWORD:
        return "Error: LINE_EMAIL or LINE_PASSWORD not found in environment."
        
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            if not page: return "Error: LINE extension page not found."
            
            if await line_utils.is_logged_in(page):
                return json.dumps({"status": "success", "message": "Already logged in."})
            
            login_result = await line_utils.perform_login(page, LINE_EMAIL, LINE_PASSWORD)
            
            if login_result["status"] == "mfa_needed":
                print(f"MFA_CODE_FOUND:{login_result['code']}")
                # Wait for up to 5 minutes for user to verify on phone
                success = await line_utils.wait_for_login_success(page, timeout_sec=300)
                if success:
                    return json.dumps({"status": "success", "message": "Login successful after MFA."})
                else:
                    screenshot_path = SCREENSHOT_DIR / "login_timeout.png"
                    await page.screenshot(path=screenshot_path)
                    return json.dumps({"status": "error", "error": "Login timed out waiting for MFA.", "screenshot": str(screenshot_path)})
            
            elif login_result["status"] == "pending":
                success = await line_utils.wait_for_login_success(page, timeout_sec=30)
                if success:
                    return json.dumps({"status": "success", "message": "Login successful."})
                else:
                    return json.dumps({"status": "error", "error": "Login triggered but could not verify success."})
            
            return json.dumps(login_result)
        except Exception as e:
            return f"Error: {str(e)}"

@mcp.tool()
async def prepare_line_instance(port: int = CDP_PORT, profile_name: str = DEFAULT_PROFILE) -> str:
    bm = BrowserManager(port=port, profile_name=profile_name)
    result = bm.prepare_instance()
    return json.dumps(result)

@mcp.tool()
async def find_chats(keyword: str, port: int = CDP_PORT) -> str:
    """Search for chats (private or group) by keyword and return a list with types."""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            if not page: return "Error: LINE extension page not found."
            await page.bring_to_front()
            
            if not await line_utils.is_logged_in(page):
                return json.dumps({"status": "error", "error": "Not logged in. Please call 'login_line' first."})
                
            matches = await line_utils.find_chats(page, keyword)
            screenshot_path = SCREENSHOT_DIR / f"find_chats_{keyword}.png"
            await page.screenshot(path=screenshot_path)
            
            return json.dumps({
                "status": "success", 
                "keyword": keyword, 
                "count": len(matches), 
                "chats": matches,
                "screenshot": str(screenshot_path)
            })
        except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
async def open_chat(chat_name: str, chat_type: str, chat_id: str, port: int = CDP_PORT) -> str:
    """Opens a specific chat by unique chat_id. Requires chat_id for precise matching."""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            if not page: return "Error: LINE extension page not found."
            await page.bring_to_front()
            await page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
            
            if not await line_utils.is_logged_in(page):
                return json.dumps({"status": "error", "error": "Not logged in. Please call 'login_line' first."})
                
            result = await line_utils.open_chat(page, chat_name, chat_type, chat_id)
            screenshot_path = SCREENSHOT_DIR / f"open_chat_{chat_name}.png"
            await page.screenshot(path=screenshot_path)
            result["screenshot"] = str(screenshot_path)
            return json.dumps(result)
        except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
async def send_line_message(chat_name: str, text: str, chat_id: Optional[str] = None, port: int = CDP_PORT) -> str:
    """Sends a message to a chat. Uses chat_id for precise matching if provided."""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            if not page: return "Error: LINE extension page not found."
            await page.bring_to_front()
            selection = await line_utils.select_chat(page, chat_name, chat_id)
            if selection["status"] not in ["success"]: return json.dumps(selection)
            await line_utils.send_message(page, text)
            return json.dumps({"status": "success", "chat": chat_name, "text": text})
        except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
async def get_line_messages(chat_name: str, limit: int = 10, chat_id: Optional[str] = None, port: int = CDP_PORT) -> str:
    """Retrieves message history from a chat. Uses chat_id for precise matching if provided."""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            context = browser.contexts[0]
            page = await line_utils.get_line_page(context)
            if not page: return "Error: LINE extension page not found."
            await page.bring_to_front()
            selection = await line_utils.select_chat(page, chat_name, chat_id)
            if selection["status"] not in ["success"]: return json.dumps(selection)
            messages = await line_utils.extract_messages(page, owner_name=OWNER_NAME, chat_name=chat_name)
            recent = messages[-limit:] if limit > 0 else messages
            return json.dumps({"status": "success", "chat": chat_name, "count": len(recent), "messages": recent})
        except Exception as e: return f"Error: {str(e)}"

@mcp.tool()
async def run_task(chat_name: str, task: str, chat_id: Optional[str] = None, port: int = CDP_PORT, model: str = DEFAULT_MODEL) -> str:
    """Runs an AI-driven task for a specific chat. Uses chat_id for precise matching if provided."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key: return "Error: GOOGLE_API_KEY not found."
    venv_python = sys.executable
    run_script = os.path.join(os.path.dirname(__file__), "run_engine.py")
    cmd = [venv_python, run_script, "--chat_name", chat_name, "--task", task, "--port", str(port), "--model", model]
    if chat_id:
        cmd.extend(["--chat_id", chat_id])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return json.dumps({"status": "completed" if result.returncode == 0 else "failed", "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    except Exception as e: return f"Error running task: {str(e)}"

if __name__ == "__main__":
    mcp.run()
