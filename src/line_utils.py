import asyncio
from typing import List, Dict, Optional, Any
from config import EXTENSION_ID, HERMES_PREFIX, MESSAGE_INPUT_SELECTOR, CHATROOM_HEADER_SELECTOR, \
    CHATLIST_ITEM_TITLE_SELECTOR, CHATLIST_ITEM_SELECTOR, CHATROOM_CONTAINER_SELECTOR, \
    MESSAGE_ITEM_SELECTOR, MESSAGE_CONTENT_SELECTOR, MESSAGE_TIME_SELECTOR, SENDER_NAME_SELECTOR

async def get_line_page(context: Any) -> Any:
    """Finds the active LINE Extension page."""
    for page in context.pages:
        if EXTENSION_ID in page.url:
            return page
    return None

async def select_chat(page: Any, chat_name: str) -> Dict[str, Any]:
    """
    Ensures the correct chat is selected in the UI using strict title matching.
    
    Technical Notes:
    - Automatically switches to the 'CHATS' navigation tab to prevent opening 
      profile overlays from the 'Friends' tab.
    - Clears and performs a fresh search to handle lazy-loaded or hidden items.
    - Uses 'force=True' on click to bypass pointer-events interception by the 
      outer button wrapper in the LINE UI.
    """
    try:
        # 0. Ensure we are in the 'CHATS' tab
        await page.evaluate('''() => {
            const icons = Array.from(document.querySelectorAll('button, [role="button"], a'));
            const chatIcon = icons.find(el => 
                (el.innerText && el.innerText.includes('Chat')) || 
                (el.getAttribute('aria-label') && el.getAttribute('aria-label').includes('Chat'))
            );
            if (chatIcon) chatIcon.click();
        }''')
        await asyncio.sleep(1)

        # 1. Check current header first
        header_locator = page.locator(CHATROOM_HEADER_SELECTOR).first
        if await header_locator.is_visible():
            text = (await header_locator.inner_text()).strip()
            # Strict header check: must match name and NOT contain group count parenthesis
            if text == chat_name or (chat_name in text and "(" not in text):
                return {"status": "success", "info": f"Chat '{chat_name}' is already selected."}

        # 2. Perform a search to be sure
        from config import SEARCH_INPUT_SELECTOR
        search_input = page.locator(SEARCH_INPUT_SELECTOR).first
        await search_input.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await search_input.fill(chat_name)
        await asyncio.sleep(2)

        # 3. Click the target item in the list
        title_locator = page.locator(CHATLIST_ITEM_TITLE_SELECTOR)
        count = await title_locator.count()
        target_item = None
        for i in range(count):
            loc = title_locator.nth(i)
            text = await loc.inner_text()
            if text.strip() == chat_name:
                target_item = loc
                break
        
        # Fallback: if strict match fails, try partial but ensure no parenthesis (group indicator)
        if not target_item:
            for i in range(count):
                loc = title_locator.nth(i)
                text = await loc.inner_text()
                if chat_name in text.strip() and "(" not in text:
                    target_item = loc
                    break
        
        if target_item:
            await target_item.click(force=True)
            await asyncio.sleep(2)
            return {"status": "success"}
        
        return {"status": "not_found", "error": f"Could not find chat containing '{chat_name}'"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def extract_messages(page: Any, owner_name: str = "Owner", chat_name: str = "Chat") -> List[Dict[str, Any]]:
    """
    Retrieves messages from the active chatroom.
    
    Technical Notes:
    - DOM Quirk: LINE Extension's message_list container often lists the newest 
      messages at the TOP of the DOM tree. 
    - Self-Detection: Standard CSS classes are randomized. We rely on the 
      'data-direction=reverse' attribute and 'justifyContent' flex styles.
    - Sender Logic: 
        - If self + [Hermes] -> 'Hermes'
        - If self -> owner_name
        - If other -> Grab name from SENDER_NAME_SELECTOR or fallback to chat_name
    - Chronological Order: The final list is reversed to ensure the Python Engine 
      receives Oldest-First order (msgs[-1] is the latest).
    """
    # Force scroll to bottom
    await page.evaluate(f'''() => {{
        const chatroom = document.querySelector('{CHATROOM_CONTAINER_SELECTOR}');
        if (chatroom) {{
            chatroom.scrollTop = chatroom.scrollHeight;
        }}
    }}''')
    await asyncio.sleep(1.5)
    
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
            
            // RELIABLE SELF-DETECTION
            const direction = msg.getAttribute('data-direction');
            const style = window.getComputedStyle(msg);
            const isSelf = direction === 'reverse' || 
                           style.justifyContent === 'flex-end' ||
                           (msgText && msgText.startsWith(prefix));

            // SENDER DETERMINATION
            let sender = "";
            if (isSelf) {{
                sender = msgText.startsWith(prefix) ? "Hermes" : ownerName;
            }} else {{
                const nameEl = msg.querySelector('{SENDER_NAME_SELECTOR}');
                sender = nameEl ? nameEl.innerText.trim() : chatName;
            }}

            results.push({{
                sender: sender,
                text: msgText.replace(prefix, "").trim(),
                timestamp: timestamp
            }});
        }});
        
        // Reverse to maintain Chronological Order (Oldest -> Newest)
        return results.reverse();
    }}
    """
    try:
        data = await page.evaluate(script)
        return data if data else []
    except Exception as e:
        print(f"Extraction Error: {e}")
        return []

async def send_message(page: Any, text: str) -> None:
    message_area = page.locator(MESSAGE_INPUT_SELECTOR).first
    await message_area.click()
    prefixed_text = f"{HERMES_PREFIX} {text}"
    await message_area.fill(prefixed_text)
    await page.keyboard.press("Enter")
