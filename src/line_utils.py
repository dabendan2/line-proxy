import asyncio
import re
from typing import List, Dict, Optional, Any
from config import EXTENSION_ID, HERMES_PREFIX, MESSAGE_INPUT_SELECTOR, CHATROOM_HEADER_SELECTOR, \
    CHATLIST_ITEM_TITLE_SELECTOR, FRIEND_LIST_ITEM_TITLE_SELECTOR, CHATLIST_ITEM_SELECTOR, CHATROOM_CONTAINER_SELECTOR, \
    MESSAGE_ITEM_SELECTOR, MESSAGE_CONTENT_SELECTOR, MESSAGE_TIME_SELECTOR, SENDER_NAME_SELECTOR

async def get_line_page(context: Any) -> Any:
    ext_url = f"chrome-extension://{EXTENSION_ID}/index.html"
    # 1. Look for existing page
    for page in context.pages:
        if EXTENSION_ID in page.url:
            # If it's an error page, force navigation
            if "chrome-error" in page.url:
                await page.goto(ext_url)
                await asyncio.sleep(2)
            return page
    
    # 2. If not found, try to repurpose any blank/error page
    for page in context.pages:
        if "chrome-error" in page.url or "about:blank" in page.url:
            await page.goto(ext_url)
            await asyncio.sleep(2)
            return page
            
    # 3. Last resort: Create new page (usually shouldn't happen with the launcher)
    try:
        page = await context.new_page()
        await page.goto(ext_url)
        await asyncio.sleep(2)
        return page
    except:
        return None

async def is_logged_in(page: Any) -> bool:
    """Checks if the user is currently logged into the LINE extension."""
    try:
        # Check for presence of common elements in a logged-in state
        friend_btn = page.locator('[aria-label="Friend"]').first
        chat_btn = page.locator('[aria-label="Chat"]').first
        return await friend_btn.is_visible() or await chat_btn.is_visible()
    except:
        return False

async def perform_login(page: Any, email: str, password: str) -> Dict[str, Any]:
    """Attempts to fill in credentials and trigger login."""
    try:
        target = page
        # Handle if login is in an iframe
        for frame in page.frames:
            if "login" in frame.url or "auth" in frame.url:
                target = frame
                break
        
        email_field = target.locator("input[type='email'], input[type='text']").first
        password_field = target.locator("input[type='password']").first
        
        if not await email_field.is_visible(timeout=5000):
            return {"status": "error", "error": "Login fields not found."}
            
        await email_field.fill(email)
        await password_field.fill(password)
        
        login_btn = target.locator("button:has-text('Log in'), button.btn_login, .login_btn, button[type='submit']").first
        if await login_btn.is_visible():
            await login_btn.click()
        else:
            await password_field.press("Enter")
            
        # Wait for MFA or Success
        await asyncio.sleep(5)
        
        # Check for MFA code
        mfa_code = None
        for frame in page.frames:
            code_el = frame.locator(".verification_code, .code, .mfa_code, div[class*='code']").first
            if await code_el.is_visible():
                mfa_code = await code_el.inner_text()
                if mfa_code and len(mfa_code.strip()) >= 4:
                    break
        
        if mfa_code:
            return {"status": "mfa_needed", "code": mfa_code.strip()}
            
        return {"status": "pending", "message": "Login triggered, checking state..."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def wait_for_login_success(page: Any, timeout_sec: int = 300) -> bool:
    """Polls for successful login for a given timeout."""
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout_sec:
        if await is_logged_in(page):
            return True
        await asyncio.sleep(5)
    return False

async def select_chat(page: Any, chat_name: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Idempotent chat selection: stays put if already there, otherwise searches and opens."""
    if not await is_logged_in(page):
        return {"status": "error", "error": "Not logged in. Please use the login_line tool first."}
    
    header_locator = page.locator(CHATROOM_HEADER_SELECTOR).first
    input_locator = page.locator(MESSAGE_INPUT_SELECTOR).first
    
    try:
        # Robust verification: Header MUST match AND Input Area MUST be ready
        if await header_locator.is_visible(timeout=1000) and await input_locator.is_visible(timeout=1000):
            header_text = await header_locator.inner_text()
            actual_name = re.sub(r'\s+', ' ', header_text).strip()
            norm_target = re.sub(r'\s+', ' ', chat_name).strip()
            
            # If chat_id is provided, we CANNOT rely on name alone for idempotency 
            # because different rooms (e.g. private vs group) might have same name.
            # However, the header doesn't show the ID. 
            # Safe approach: if chat_id is provided, we ALWAYS perform search to be sure,
            # unless we can find the data-mid of the active chat (usually not in header).
            if actual_name == norm_target and not chat_id:
                return {"status": "success", "info": f"Chat '{chat_name}' already selected and ready."}
    except:
        pass
        
    # If not selected or input not ready, we search and open
    chats = await find_chats(page, chat_name)
    if isinstance(chats, dict) and chats.get("status") == "error":
        return chats
        
    if not chats:
        return {"status": "not_found", "error": f"No chat found with name '{chat_name}'"}
    
    # Pick target by chat_id (Required Path)
    target = None
    if chat_id:
        target = next((c for c in chats if c["chat_id"] == chat_id), None)
    else:
        # If no chat_id provided, find the exact name match to get its ID
        target = next((c for c in chats if c["name"] == chat_name), None)
    
    if not target or not target.get("chat_id"):
        return {"status": "error", "error": f"Could not resolve unique chat_id for '{chat_name}'. Search results: {len(chats)}"}
        
    return await open_chat(page, target["name"], target["type"], target["chat_id"])

async def find_chats(page: Any, keyword: str) -> List[Dict[str, str]]:
    """Finds chats matching the keyword with their types and unique chat_ids."""
    try:
        # 1. Navigation to Friends Tab
        friend_btn = page.locator('[aria-label="Friend"]').first
        is_friend_visible = await friend_btn.is_visible()
        if is_friend_visible:
            await friend_btn.click()
            await asyncio.sleep(0.5)

        # 2. Search
        search_input = page.locator('input[placeholder*="Search"], input[placeholder*="搜尋"], .search_input').first
        await search_input.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await search_input.fill(keyword)
        
        # Wait for results to stabilize
        await asyncio.sleep(1.5) # Increased for stability
        
        # 3. Scrape results using Top-Down classification
        script = """
        (keyword) => {
            try {
                // A. Identify headers
                const headerEls = Array.from(document.querySelectorAll('*')).filter(el => {
                    const t = el.innerText ? el.innerText.trim() : "";
                    return (t === "群組" || t === "好友" || t === "Groups" || t === "Friends") && el.offsetHeight > 0;
                });
                
                const sections = headerEls.map(el => {
                    const t = el.innerText.trim();
                    return {
                        type: (t === "群組" || t === "Groups") ? "group" : "private",
                        top: el.getBoundingClientRect().top
                    };
                }).sort((a, b) => a.top - b.top);
                
                // B. Get all potential items
                const selectors = ['*[class*="item"]', '*[class*="Item"]', '.search_item'];
                const allItems = Array.from(document.querySelectorAll(selectors.join(','))).filter(el => el.offsetHeight > 0);
                
                // C. Filter out children
                const rootItems = allItems.filter(el => {
                    return !allItems.some(other => other !== el && other.contains(el));
                });
                
                const results = [];
                rootItems.forEach(el => {
                    const titleEl = el.querySelector('[class*="title"], [class*="name_box"], .search_text, [class*="name"]');
                    if (!titleEl) return;
                    
                    const name = titleEl.innerText.trim();
                    if (!name.toLowerCase().includes(keyword.toLowerCase())) return;
                    
                    const chatId = el.getAttribute('data-mid') || "";
                    const top = el.getBoundingClientRect().top;
                    
                    let type = "private";
                    for (let i = sections.length - 1; i >= 0; i--) {
                        if (top > sections[i].top) {
                            type = sections[i].type;
                            break;
                        }
                    }
                    results.push({ name, type, chat_id: chatId });
                });
                return results;
            } catch (e) {
                return { "error": e.toString() };
            }
        }
        """
        matches = await page.evaluate(script, keyword)
        if isinstance(matches, dict) and "error" in matches:
            raise Exception(f"JS Error: {matches['error']}")
            
        # Deduplicate by chat_id
        unique_matches = {}
        for m in matches:
            cid = m.get("chat_id")
            if cid:
                if cid not in unique_matches:
                    unique_matches[cid] = m
            else:
                key = f"{m['name']}_{m['type']}"
                if key not in unique_matches:
                    unique_matches[key] = m
        
        return list(unique_matches.values())
    except Exception as e:
        return {"status": "error", "error": f"Failed to find chats: {str(e)}"}

async def open_chat(page: Any, chat_name: str, chat_type: str, chat_id: str) -> Dict[str, Any]:
    """Navigates to and opens a specific chat using ONLY chat_id for selection."""
    try:
        # 1. Use chat_id exclusively for selection
        chat_id_locator = page.locator(f'[data-mid="{chat_id}"]').first
        if await chat_id_locator.is_visible(timeout=3000):
            target_el = chat_id_locator
        else:
            return {"status": "error", "error": f"Could not find chat with precise ID '{chat_id}' (Name: {chat_name}). Selection aborted."}
        
        # Perform click
        await target_el.scroll_into_view_if_needed()
        await target_el.click(force=True)
        await asyncio.sleep(0.5)

        # Profile Bridge: Some searches open a profile card first
        chat_btn = page.locator('button:has-text("Chat"), button:has-text("聊天"), [role="button"]:has-text("Chat")').first
        if await chat_btn.is_visible(timeout=2000):
            await chat_btn.click()
            await asyncio.sleep(1)
        
        # Verification: Both Header and Input Area must be visible
        header_locator = page.locator(CHATROOM_HEADER_SELECTOR).first
        input_locator = page.locator(MESSAGE_INPUT_SELECTOR).first
        
        # Normalize chat_name for comparison
        norm_target_name = re.sub(r'\s+', ' ', chat_name).strip()
        
        for _ in range(10):
            h_vis = await header_locator.is_visible()
            i_vis = await input_locator.is_visible()
            if h_vis and i_vis:
                header_text = await header_locator.inner_text()
                actual_name = re.sub(r'\s+', ' ', header_text).strip()
                
                # If we have a chat_id, we've already clicked the right thing by ID.
                # We prioritize success but still log/verify name if possible.
                # We accept partial match if chat_id is used.
                if chat_id or actual_name == norm_target_name or chat_name in actual_name:
                    return {"status": "success", "chat_name": chat_name, "type": chat_type, "chat_id": chat_id}
            await asyncio.sleep(0.5)

        return {"status": "error", "error": f"Verification failed. Header visible: {h_vis}, Input visible: {i_vis}. Target: {norm_target_name}"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def extract_messages(page: Any, owner_name: str = "Owner", chat_name: str = "Chat") -> List[Dict[str, Any]]:
    # TIME INHERITANCE
    try:
        chatroom = CHATROOM_CONTAINER_SELECTOR
        await page.evaluate(f'''(sel) => {{
            const el = document.querySelector(sel);
            if (el) el.scrollTop = el.scrollHeight;
        }}''', chatroom)
        
        script = f"""
        () => {{
            const results = [];
            const prefix = "{HERMES_PREFIX}";
            const ownerName = "{owner_name}";
            const chatName = "{chat_name}";
            const chatroom = document.querySelector('{CHATROOM_CONTAINER_SELECTOR}');
            if (!chatroom) throw new Error('Chatroom container not found. Check if the chat is properly opened.');
            const items = Array.from(chatroom.querySelectorAll('{MESSAGE_ITEM_SELECTOR}')).filter(el => {{
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetHeight > 0;
            }});
            items.forEach(msg => {{
                const contentEl = msg.querySelector('{MESSAGE_CONTENT_SELECTOR}');
                if (!contentEl) return;
                const msgText = contentEl.innerText.trim();
                const timeEl = msg.querySelector('{MESSAGE_TIME_SELECTOR}');
                const timestamp = timeEl ? timeEl.innerText.trim() : "";
                const direction = msg.getAttribute('data-direction');
                const style = window.getComputedStyle(msg);
                const isSelf = direction === 'reverse' || style.justifyContent === 'flex-end' || (msgText && msgText.startsWith(prefix));
                let sender = "";
                if (isSelf) sender = msgText.startsWith(prefix) ? "Hermes" : ownerName;
                else {{ const nameEl = msg.querySelector('{SENDER_NAME_SELECTOR}'); sender = nameEl ? nameEl.innerText.trim() : chatName; }}
                results.push({{ sender, text: msgText.replace(prefix, "").trim(), timestamp }});
            }});
            const chronMessages = results.reverse();
            for (let i = chronMessages.length - 2; i >= 0; i--) {{
                if (!chronMessages[i].timestamp && chronMessages[i+1].timestamp && chronMessages[i].sender === chronMessages[i+1].sender) {{
                    chronMessages[i].timestamp = chronMessages[i+1].timestamp;
                }}
            }}
            return chronMessages;
        }}
        """
        data = await page.evaluate(script)
        return data if data else []
    except Exception as e: raise e

async def send_message(page: Any, text: str) -> None:
    message_area = page.locator(MESSAGE_INPUT_SELECTOR).first
    await message_area.click()
    prefixed_text = f"{HERMES_PREFIX} {text}"
    await message_area.fill(prefixed_text)
    await page.keyboard.press("Enter")
