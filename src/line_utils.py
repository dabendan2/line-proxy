import asyncio
from typing import List, Dict, Optional, Any
from config import EXTENSION_ID, HERMES_PREFIX, MESSAGE_INPUT_SELECTOR, CHATROOM_HEADER_SELECTOR, \
    CHATLIST_ITEM_TITLE_SELECTOR, FRIEND_LIST_ITEM_TITLE_SELECTOR, CHATLIST_ITEM_SELECTOR, CHATROOM_CONTAINER_SELECTOR, \
    MESSAGE_ITEM_SELECTOR, MESSAGE_CONTENT_SELECTOR, MESSAGE_TIME_SELECTOR, SENDER_NAME_SELECTOR

async def get_line_page(context: Any) -> Any:
    for page in context.pages:
        if EXTENSION_ID in page.url: return page
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

async def select_chat(page: Any, chat_name: str) -> Dict[str, Any]:
    """Idempotent chat selection: stays put if already there, otherwise searches and opens."""
    if not await is_logged_in(page):
        return {"status": "error", "error": "Not logged in. Please use the login_line tool first."}
    
    header_locator = page.locator(CHATROOM_HEADER_SELECTOR).first
    input_locator = page.locator(MESSAGE_INPUT_SELECTOR).first
    
    try:
        # Robust verification: Header MUST match AND Input Area MUST be ready
        if await header_locator.is_visible(timeout=1000) and await input_locator.is_visible(timeout=1000):
            actual_name = (await header_locator.inner_text()).strip()
            if actual_name == chat_name:
                return {"status": "success", "info": f"Chat '{chat_name}' already selected and ready."}
    except:
        pass
        
    # If not selected or input not ready, we search and open
    chats = await list_chats(page, chat_name)
    # Check if we got an error dictionary instead of a list
    if isinstance(chats, dict) and chats.get("status") == "error":
        return chats
        
    if not chats:
        return {"status": "not_found", "error": f"No chat found with name '{chat_name}'"}
    
    # Pick EXACT match. Fallback to first ONLY if no exact match but we should ideally error.
    # Given the user's preference for strict matching:
    target = next((c for c in chats if c["name"] == chat_name), None)
    
    if not target:
        return {"status": "error", "error": f"No exact match found for '{chat_name}' in search results."}
        
    return await open_chat(page, target["name"], target["type"])

async def list_chats(page: Any, keyword: str) -> List[Dict[str, str]]:
    """Lists chats matching the keyword with their types."""
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
                    
                    const top = el.getBoundingClientRect().top;
                    
                    let type = "private";
                    for (let i = sections.length - 1; i >= 0; i--) {
                        if (top > sections[i].top) {
                            type = sections[i].type;
                            break;
                        }
                    }
                    results.push({ name, type });
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
        return matches
    except Exception as e:
        # Stop swallowing errors. Return status: error so the tool knows it failed.
        return {"status": "error", "error": f"Failed to list chats: {str(e)}"}

async def open_chat(page: Any, chat_name: str, chat_type: str) -> Dict[str, Any]:
    """Navigates to and opens a specific chat by name and type."""
    try:
        # Determine selector based on type to improve precision
        title_selector = FRIEND_LIST_ITEM_TITLE_SELECTOR if chat_type == "private" else CHATLIST_ITEM_TITLE_SELECTOR
        list_locator = page.locator(title_selector)
        
        count = await list_locator.count()
        target_idx = -1
        
        # STRICT EXACT MATCH ONLY
        for i in range(count):
            text = (await list_locator.nth(i).inner_text()).strip()
            if text == chat_name:
                target_idx = i
                break
        
        if target_idx == -1:
            # Last ditch effort: search across both if type-specific fails (for robustness)
            fallback_locator = page.locator(f"{CHATLIST_ITEM_TITLE_SELECTOR}, {FRIEND_LIST_ITEM_TITLE_SELECTOR}")
            f_count = await fallback_locator.count()
            for i in range(f_count):
                if (await fallback_locator.nth(i).inner_text()).strip() == chat_name:
                    target_idx = i
                    list_locator = fallback_locator
                    break
                    
        if target_idx != -1:
            target_el = list_locator.nth(target_idx)
            await target_el.scroll_into_view_if_needed()
            await target_el.click(force=True)
            await asyncio.sleep(0.5)
        else:
            return {"status": "error", "error": f"Could not find exact match for chat '{chat_name}' with type '{chat_type}' to open."}

        # Profile Bridge for Private Chats
        if chat_type == "private":
            chat_btn = page.locator('button:has-text("Chat"), button:has-text("聊天"), [role="button"]:has-text("Chat")').first
            if await chat_btn.is_visible(timeout=2000):
                await chat_btn.click()
                await asyncio.sleep(1)
        
        # Verification: Both Header and Input Area must be visible
        header_locator = page.locator(CHATROOM_HEADER_SELECTOR).first
        input_locator = page.locator(MESSAGE_INPUT_SELECTOR).first
        
        for _ in range(10):
            if await header_locator.is_visible() and await input_locator.is_visible():
                actual_name = (await header_locator.inner_text()).strip()
                if actual_name == chat_name:
                    return {"status": "success", "chat_name": chat_name, "type": chat_type}
            await asyncio.sleep(0.5)

        return {"status": "error", "error": "Could not verify chatroom header and input area are ready."}
        
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
