import asyncio
import re
import json
from typing import List, Dict, Optional, Any
from utils.config import EXTENSION_ID, HERMES_PREFIX, MESSAGE_INPUT_SELECTOR, CHATROOM_HEADER_SELECTOR, \
    CHATLIST_ITEM_TITLE_SELECTOR, FRIEND_LIST_ITEM_TITLE_SELECTOR, CHATLIST_ITEM_SELECTOR, CHATROOM_CONTAINER_SELECTOR, \
    MESSAGE_ITEM_SELECTOR, MESSAGE_CONTENT_SELECTOR, MESSAGE_TIME_SELECTOR, SENDER_NAME_SELECTOR, FILE_INPUT_SELECTOR

async def get_line_page(context: Any) -> Any:
    ext_url = f"chrome-extension://{EXTENSION_ID}/index.html"
    target_page = None
    
    # Wait for context to sync pages
    for _ in range(10):
        if context.pages:
            break
        await asyncio.sleep(0.2)
    
    # 1. First pass: Find the BEST target (one that is already logged in/on a functional route)
    for page in context.pages:
        if EXTENSION_ID in page.url:
            if any(route in page.url for route in ["#/friends", "#/chats", "#/timeline"]):
                target_page = page
                break
    
    # 2. Second pass: Find any extension page if no functional route found
    if not target_page:
        for page in context.pages:
            if EXTENSION_ID in page.url:
                target_page = page
                break
    
    # 3. Third pass: Repurpose blank/error pages
    if not target_page:
        for page in context.pages:
            if "chrome-error" in page.url or "about:blank" in page.url:
                await page.goto(ext_url)
                await asyncio.sleep(2)
                target_page = page
                break
                
    # 4. Create new if still not found
    if not target_page:
        try:
            target_page = await context.new_page()
            await target_page.goto(ext_url)
            await asyncio.sleep(2)
        except:
            return None
            
    # 5. SINGLETON ENFORCEMENT
    if target_page:
        # Don't close background pages or internal extension pages that might be needed
        for page in context.pages:
            try:
                if page != target_page and not any(ext in page.url for ext in ["devtools", "background", "service-worker"]):
                    # If it's another LINE UI page, close it to keep focus
                    if EXTENSION_ID in page.url:
                        await page.close()
            except:
                pass
                
    return target_page

async def is_logged_in(page: Any, timeout_ms: int = 3000) -> bool:
    """Checks if the user is currently logged into the LINE extension with robust fallbacks."""
    try:
        # 1. Force get real URL from window context to avoid Playwright property lag
        real_url = await page.evaluate("window.location.href")
        
        # 2. Wait a bit if we are on the root or loading page
        if real_url.endswith("#/") or "index.html" not in real_url:
            await asyncio.sleep(1.0)
            real_url = await page.evaluate("window.location.href")
            
        # 3. Permissive check: if indicators exist, we are logged in regardless of URL
        indicators = page.locator('[aria-label="Friend"], [aria-label="Chat"], .nav_item, [class*="nav"]')
        count = await indicators.count()
        
        if count > 0:
            return True
            
        # 4. Fallback to URL check
        if "index.html" in real_url and "#/login" not in real_url and not real_url.endswith("#/"):
            return True
            
        return False
    except Exception as e:
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
    norm_target_name = re.sub(r'\s+', ' ', chat_name).strip().lower()
    
    if chat_id:
        target = next((c for c in chats if c["chat_id"] == chat_id), None)
    else:
        # Robust selection: 
        # 1. Look for exact normalized name match
        # 2. Prioritize private chats if multiple partial matches exist
        exact_matches = [c for c in chats if re.sub(r'\s+', ' ', c["name"]).strip().lower() == norm_target_name]
        if exact_matches:
            # If multiple exact name matches (rare), prioritize private
            target = next((c for c in exact_matches if c["type"] == "private"), exact_matches[0])
        else:
            # Fallback to partial match
            partial_matches = [c for c in chats if norm_target_name in re.sub(r'\s+', ' ', c["name"]).strip().lower()]
            if partial_matches:
                target = next((c for c in partial_matches if c["type"] == "private"), partial_matches[0])
    
    if not target or not target.get("chat_id"):
        return {"status": "error", "error": f"Could not resolve unique chat_id for '{chat_name}'. Found {len(chats)} candidates."}
        
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
        
        # EVENT-DRIVEN: Wait for results to reflect the keyword or "No results"
        # This prevents the race condition where evaluate() runs before filtering is done.
        try:
            await page.wait_for_function(
                """(kw) => {
                    const items = document.querySelectorAll('[class*="title"], [class*="name"]');
                    const text = Array.from(items).map(i => i.innerText).join(' ');
                    const bodyText = document.body.innerText;
                    return text.includes(kw) || bodyText.includes('No results') || bodyText.includes('查裝結果') || bodyText.includes('沒有符合條件');
                }""", 
                keyword,
                timeout=3000
            )
        except:
            # Fallback to a small sleep if wait_for_function times out (it might be a partial match)
            await asyncio.sleep(1)
        
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

        # Profile Bridge: Some searches open a profile card first
        chat_btn = page.locator('button:has-text("Chat"), button:has-text("聊天"), [role="button"]:has-text("Chat")').first
        try:
            # Event-driven: Only wait if the button appears
            await chat_btn.wait_for(state="visible", timeout=2000)
            await chat_btn.click()
        except:
            # If no chat button appears within 2s, assume we're already in the chat or it's direct
            pass
        
        # Verification: Both Header and Input Area must be visible
        header_locator = page.locator(CHATROOM_HEADER_SELECTOR).first
        input_locator = page.locator(MESSAGE_INPUT_SELECTOR).first
        
        # Normalize chat_name for comparison
        norm_target_name = re.sub(r'\s+', ' ', chat_name).strip()
        
        # Event-driven: Wait for both header and input to be visible
        try:
            await asyncio.gather(
                header_locator.wait_for(state="visible", timeout=5000),
                input_locator.wait_for(state="visible", timeout=5000)
            )
            header_text = await header_locator.inner_text()
            actual_name = re.sub(r'\s+', ' ', header_text).strip()
            
            if chat_id or actual_name == norm_target_name or chat_name in actual_name:
                return {"status": "success", "chat_name": chat_name, "type": chat_type, "chat_id": chat_id}
        except Exception as e:
            return {"status": "error", "error": f"Verification failed: {str(e)}. Target: {norm_target_name}"}

        return {"status": "error", "error": f"Verification failed. Target: {norm_target_name}"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def extract_messages(page: Any, owner_name: str = "Owner", chat_name: str = "Chat") -> List[Dict[str, Any]]:
    # TIME INHERITANCE & DATE TRACKING
    try:
        chatroom = CHATROOM_CONTAINER_SELECTOR
        await page.evaluate(f'''(sel) => {{
            const el = document.querySelector(sel);
            if (el) el.scrollTop = el.scrollHeight;
        }}''', chatroom)
        
        script = f"""
        () => {{
            const results = [];
            const prefix = {json.dumps(HERMES_PREFIX)};
            const ownerName = {json.dumps(owner_name)};
            const chatName = {json.dumps(chat_name)};
            const chatroom = document.querySelector({json.dumps(CHATROOM_CONTAINER_SELECTOR)});
            if (!chatroom) throw new Error('Chatroom container not found.');
            
            // Get all elements in order: messages AND date dividers
            const items = Array.from(chatroom.querySelectorAll({json.dumps(MESSAGE_ITEM_SELECTOR)} + ', [class*="messageDate-module__date__"]')).filter(el => {{
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetHeight > 0;
            }});
            
            let currentDate = "";
            items.forEach(el => {{
                // Check if it's a date divider
                if (el.className.includes('messageDate-module__date__')) {{
                    currentDate = el.innerText.trim();
                    return;
                }}
                
                // It's a message
                const contentEl = el.querySelector({json.dumps(MESSAGE_CONTENT_SELECTOR)});
                if (!contentEl) return;
                
                // CLONE AND CLEAN: Remove time and status labels to avoid text leakage
                const cleanContent = contentEl.cloneNode(true);
                const toRemove = cleanContent.querySelectorAll({json.dumps(MESSAGE_TIME_SELECTOR)} + ', [class*="read"], [class*="status"]');
                toRemove.forEach(r => r.remove());
                
                const msgText = cleanContent.innerText.trim();
                const timeEl = el.querySelector({json.dumps(MESSAGE_TIME_SELECTOR)});
                const timestamp = timeEl ? timeEl.innerText.trim() : "";
                const direction = el.getAttribute('data-direction');
                const style = window.getComputedStyle(el);
                const isSelf = direction === 'reverse' || style.justifyContent === 'flex-end' || (msgText && msgText.startsWith(prefix));
                
                let sender = "";
                if (isSelf) sender = msgText.startsWith(prefix) ? "Hermes" : ownerName;
                else {{ 
                    const nameEl = el.querySelector({json.dumps(SENDER_NAME_SELECTOR)}); 
                    sender = nameEl ? nameEl.innerText.trim() : chatName; 
                }}
                
                results.push({{ 
                    sender, 
                    text: msgText.replace(prefix, "").trim(), 
                    timestamp,
                    date: currentDate 
                }});
            }});
            
            // 1. Chronological fix: In this DOM, querySelectorAll returns items from BOTTOM to TOP (Newest to Oldest).
            // We reverse them to ensure the array flows [Oldest -> Newest].
            const chronMessages = results.reverse(); 
            
            // 2. Time inheritance for messages in the same minute (same sender)
            // Now that it's [Oldest -> Newest], i+1 is the newer message.
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
    # Use type instead of fill because <textarea-ex> doesn't support fill
    await page.keyboard.type(prefixed_text)
    await page.keyboard.press("Enter")

async def send_image(page: Any, image_path: str) -> None:
    """Sends an image to the current chat by pasting it from the clipboard."""
    import os
    import httpx
    import base64
    
    # 1. Prepare image data (Local or URL)
    image_data_base64 = ""
    mime_type = "image/png"
    
    try:
        if image_path.startswith("http"):
            async with httpx.AsyncClient() as client:
                resp = await client.get(image_path)
                resp.raise_for_status()
                image_data_base64 = base64.b64encode(resp.content).decode("utf-8")
                mime_type = resp.headers.get("Content-Type", "image/png")
        else:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            with open(image_path, "rb") as f:
                image_data_base64 = base64.b64encode(f.read()).decode("utf-8")
                ext = os.path.splitext(image_path)[1].lower()
                if ext in [".jpg", ".jpeg"]: mime_type = "image/jpeg"
                elif ext == ".gif": mime_type = "image/gif"
                elif ext == ".webp": mime_type = "image/webp"

        # 2. Inject and Paste via JS
        # We simulate a "paste" event with a DataTransfer object containing the image file
        print(f"DEBUG: Attempting to paste image ({mime_type})")
        
        script = """
        async ({data, type}) => {
            const res = await fetch(`data:${type};base64,${data}`);
            const blob = await res.blob();
            const file = new File([blob], "image.png", { type: type });
            
            const target = document.querySelector('.message_input, [contenteditable="true"], textarea, textarea-ex');
            if (!target) throw new Error("Message input not found");
            
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            
            const pasteEvent = new ClipboardEvent('paste', {
                clipboardData: dataTransfer,
                bubbles: true,
                cancelable: true
            });
            
            target.focus();
            target.dispatchEvent(pasteEvent);
            return true;
        }
        """
        success = await page.evaluate(script, {"data": image_data_base64, "type": mime_type})
        if success:
            print("DEBUG: Paste event dispatched")
            await asyncio.sleep(2) # Wait for processing
            await page.keyboard.press("Enter")
            await asyncio.sleep(1)
        
    except Exception as e:
        print(f"Error in send_image: {e}")
        raise e
