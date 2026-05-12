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
    return await find_chat(page, chat_name)

async def find_chat(page: Any, chat_name: str) -> Dict[str, Any]:
    try:
        # 1. Navigation to Friends Tab
        friend_btn = page.locator('[aria-label="Friend"]').first
        if await friend_btn.is_visible():
            await friend_btn.click()
            try: await page.locator('[class*="friendlist"]').first.wait_for(state="visible", timeout=2000)
            except: pass

        # 2. Search
        search_input = page.locator('input[placeholder*="Search"], input[placeholder*="搜尋"], .search_input').first
        await search_input.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await search_input.fill(chat_name)
        
        # 3. Match using Locator (Strict)
        # Check both chat and friend list title selectors
        list_locator = page.locator(f"{CHATLIST_ITEM_TITLE_SELECTOR}, {FRIEND_LIST_ITEM_TITLE_SELECTOR}")
        # Use wait_for to be event-driven
        try: await list_locator.first.wait_for(state="visible", timeout=3000)
        except: pass
        
        count = await list_locator.count()
        if not isinstance(count, int): count = 0
            
        target_indices = []
        for i in range(count):
            text = (await list_locator.nth(i).inner_text()).strip()
            if chat_name in text: # Use partial match for robustness but exact is preferred
                target_indices.append(i)
        
        if len(target_indices) == 0:
            # JS Fallback
            js_matches = await page.evaluate(f'''(target) => {{
                const items = Array.from(document.querySelectorAll('*[class*="item"], *[class*="Item"], *[class*="name_box"]'));
                const res = [];
                items.forEach(el => {{
                    const text = el.innerText ? el.innerText.trim() : "";
                    if (text.includes(target) && el.offsetHeight > 0) res.push(target);
                }});
                return Array.from(new Set(res));
            }}''', chat_name)
            if not js_matches or len(js_matches) == 0:
                return {"status": "not_found", "error": f"No friend found with name '{chat_name}'"}
            if len(js_matches) > 1:
                return {"status": "ambiguous", "error": "Multiple matches found.", "matches": js_matches}
        elif len(target_indices) > 1:
            # Filter for exact match among multiple partial matches
            exact_indices = []
            for idx in target_indices:
                text = (await list_locator.nth(idx).inner_text()).strip()
                if text == chat_name:
                    exact_indices.append(idx)
            if len(exact_indices) == 1:
                target_indices = exact_indices
            else:
                return {"status": "ambiguous", "error": "Multiple matches found.", "matches": [chat_name] * len(target_indices)}

        # 4. Click (Refined: Click specifically on the title element to be safe)
        if len(target_indices) > 0:
            target_el = list_locator.nth(target_indices[0])
            await target_el.scroll_into_view_if_needed()
            await target_el.click(force=True)
            # Small sleep to allow UI update
            await asyncio.sleep(0.5)
        else:
            clicked = await page.evaluate(f'''(target) => {{
                const selectors = ['*[class*="chatlistItem-module__title"]', '*[class*="friendlistItem-module__name_box"]', '.search_text'];
                for (const sel of selectors) {{
                    const items = Array.from(document.querySelectorAll(sel));
                    const el = items.find(el => el.innerText.trim().includes(target) && el.offsetHeight > 0);
                    if (el) {{ el.click(); return true; }}
                }}
                return false;
            }}''', chat_name)
            if not clicked:
                return {"status": "error", "error": f"Found '{chat_name}' in list but failed to click it."}

        # 5. Profile Bridge
        chat_btn = page.locator('button:has-text("Chat"), button:has-text("聊天"), [role="button"]:has-text("Chat")').first
        if await chat_btn.is_visible():
            await chat_btn.click()
            await asyncio.sleep(1)
        
        # 6. Verification (Stronger)
        header_locator = page.locator(CHATROOM_HEADER_SELECTOR).first
        input_area = page.locator(MESSAGE_INPUT_SELECTOR).first
        
        # Wait for either header or input to confirm navigation
        for _ in range(5):
            if await header_locator.is_visible():
                actual_name = (await header_locator.inner_text()).strip()
                if actual_name == chat_name:
                    return {"status": "success", "chat_name": chat_name}
            if await input_area.is_visible():
                # Check header text again even if input is visible
                actual_name = (await header_locator.inner_text()).strip()
                if actual_name == chat_name:
                    return {"status": "success", "chat_name": chat_name}
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
