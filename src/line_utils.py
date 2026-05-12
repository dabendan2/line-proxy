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
    try:
        if await header_locator.is_visible(timeout=1000):
            actual_name = (await header_locator.inner_text()).strip()
            if actual_name == chat_name:
                return {"status": "success", "info": f"Chat '{chat_name}' already selected."}
    except:
        pass
        
    # If not selected, we list and pick the first match (Legacy support behavior)
    chats = await list_chats(page, chat_name)
    if not chats:
        return {"status": "not_found", "error": f"No chat found with name '{chat_name}'"}
    
    # Pick exact match if possible
    target = next((c for c in chats if c["name"] == chat_name), chats[0])
    return await open_chat(page, target["name"], target["type"])

async def list_chats(page: Any, keyword: str) -> List[Dict[str, str]]:
    """Lists chats matching the keyword with their types."""
    try:
        # 1. Navigation to Friends Tab
        friend_btn = page.locator('[aria-label="Friend"]').first
        if await friend_btn.is_visible():
            await friend_btn.click()
            await asyncio.sleep(0.5)

        # 2. Search
        search_input = page.locator('input[placeholder*="Search"], input[placeholder*="搜尋"], .search_input').first
        await search_input.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await search_input.fill(keyword)
        
        # Wait for results to stabilize
        await asyncio.sleep(1)
        
        # 3. Scrape results using JS for complex hierarchy detection
        script = """
        (keyword) => {
            const results = [];
            // Select elements that look like list items
            const selectors = [
                '[class*="chatlistItem-module__item"]', 
                '[class*="friendlistItem-module__item"]',
                '.search_item',
                '[role="button"]'
            ];
            
            const items = Array.from(document.querySelectorAll(selectors.join(',')));
            
            items.forEach(el => {
                if (el.offsetHeight === 0) return;
                
                const titleEl = el.querySelector('[class*="title"], [class*="name_box"], .search_text');
                if (!titleEl) return;
                
                const name = titleEl.innerText.trim();
                if (!name.toLowerCase().includes(keyword.toLowerCase())) return;
                
                // Determine type by looking at parent sections or icon features
                let type = "private";
                
                // Heuristic 1: Check section headers above this element
                let current = el;
                let foundType = false;
                while (current && current.parentElement) {
                    const sectionText = current.parentElement.innerText;
                    if (sectionText.includes("群組") || sectionText.includes("Group")) {
                        type = "group";
                        foundType = true;
                        break;
                    }
                    if (sectionText.includes("好友") || sectionText.includes("Friend")) {
                        type = "private";
                        foundType = true;
                        break;
                    }
                    current = current.parentElement;
                    if (current.tagName === 'BODY') break;
                }
                
                // Heuristic 2: Check for multiple avatars (group characteristic)
                if (!foundType) {
                    const avatars = el.querySelectorAll('[class*="avatar"], img');
                    if (avatars.length > 1) type = "group";
                }
                
                results.push({ name, type });
            });
            
            // Deduplicate
            return results.filter((v,i,a) => a.findIndex(t => (t.name === v.name && t.type === v.type)) === i);
        }
        """
        matches = await page.evaluate(script, keyword)
        return matches
    except Exception as e:
        print(f"Error in list_chats: {e}")
        return []

async def open_chat(page: Any, chat_name: str, chat_type: str) -> Dict[str, Any]:
    """Navigates to and opens a specific chat by name and type."""
    try:
        # Ensure we are in search mode or find the item
        # We assume list_chats might have been called, but to be safe, we re-verify visibility
        
        # Locate the item by text and try to match type-specific characteristics if possible
        # For now, we search by text and filter by type if multiple exist
        
        list_locator = page.locator(f"{CHATLIST_ITEM_TITLE_SELECTOR}, {FRIEND_LIST_ITEM_TITLE_SELECTOR}")
        count = await list_locator.count()
        
        target_idx = -1
        for i in range(count):
            text = (await list_locator.nth(i).inner_text()).strip()
            if text == chat_name:
                # In a real scenario, we'd verify type here too, but for simplicity:
                target_idx = i
                break
        
        if target_idx == -1:
            # Try partial match if exact fails
            for i in range(count):
                text = (await list_locator.nth(i).inner_text()).strip()
                if chat_name in text:
                    target_idx = i
                    break
        
        if target_idx != -1:
            target_el = list_locator.nth(target_idx)
            await target_el.scroll_into_view_if_needed()
            await target_el.click(force=True)
            await asyncio.sleep(0.5)
        else:
            return {"status": "error", "error": f"Could not find chat '{chat_name}' to open."}

        # Profile Bridge for Private Chats
        if chat_type == "private":
            chat_btn = page.locator('button:has-text("Chat"), button:has-text("聊天"), [role="button"]:has-text("Chat")').first
            if await chat_btn.is_visible(timeout=2000):
                await chat_btn.click()
                await asyncio.sleep(1)
        
        # Verification
        header_locator = page.locator(CHATROOM_HEADER_SELECTOR).first
        for _ in range(5):
            if await header_locator.is_visible():
                actual_name = (await header_locator.inner_text()).strip()
                if chat_name in actual_name:
                    return {"status": "success", "chat_name": chat_name, "type": chat_type}
            await asyncio.sleep(0.5)

        return {"status": "error", "error": "Could not verify chatroom opened."}
        
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
            if (!chatroom) return [];
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
