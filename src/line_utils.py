import asyncio
import os
from typing import List, Dict, Optional, Any
from config import EXTENSION_ID, HERMES_PREFIX, MESSAGE_INPUT_SELECTOR, CHATROOM_HEADER_SELECTOR, \
    CHATLIST_ITEM_TITLE_SELECTOR, CHATLIST_ITEM_SELECTOR, CHATROOM_CONTAINER_SELECTOR, \
    MESSAGE_ITEM_SELECTOR, MESSAGE_CONTENT_SELECTOR, MESSAGE_TIME_SELECTOR, SENDER_NAME_SELECTOR

async def get_line_page(context: Any) -> Any:
    for page in context.pages:
        if EXTENSION_ID in page.url: return page
    return None

async def select_chat(page: Any, chat_name: str) -> Dict[str, Any]:
    header_locator = page.locator(CHATROOM_HEADER_SELECTOR).first
    try:
        if await header_locator.is_visible():
            if (await header_locator.inner_text()).strip() == chat_name:
                return {"status": "success", "info": f"Chat '{chat_name}' selected."}
    except: pass
    return await find_private_chat(page, chat_name)

async def find_private_chat(page: Any, chat_name: str) -> Dict[str, Any]:
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
        list_locator = page.locator(CHATLIST_ITEM_TITLE_SELECTOR)
        # Use wait_for to be event-driven
        try: await list_locator.first.wait_for(state="visible", timeout=3000)
        except: pass
        
        count = await list_locator.count()
        if not isinstance(count, int): count = 0
            
        target_indices = []
        for i in range(count):
            text = (await list_locator.nth(i).inner_text()).strip()
            if text == chat_name:
                target_indices.append(i)
        
        if len(target_indices) == 0:
            # JS Fallback
            js_matches = await page.evaluate(f'''(target) => {{
                const items = Array.from(document.querySelectorAll('*[class*="item"], *[class*="Item"]'));
                const res = [];
                items.forEach(el => {{
                    const lines = el.innerText ? el.innerText.split('\\n').map(l => l.trim()) : [];
                    if (lines.includes(target) && el.offsetHeight > 0) res.push(target);
                }});
                return Array.from(new Set(res));
            }}''', chat_name)
            if not js_matches or len(js_matches) == 0:
                return {"status": "not_found", "error": f"No friend found with name '{chat_name}'"}
            if len(js_matches) > 1:
                return {"status": "ambiguous", "error": "Multiple matches found.", "matches": js_matches}
        elif len(target_indices) > 1:
            return {"status": "ambiguous", "error": "Multiple matches found.", "matches": [chat_name] * len(target_indices)}

        # 4. Click
        if len(target_indices) > 0:
            await list_locator.nth(target_indices[0]).click(force=True)
        else:
            await page.evaluate(f'''(target) => {{
                const items = Array.from(document.querySelectorAll('*[class*="item"], *[class*="Item"]'));
                const el = items.find(el => el.innerText.trim().split('\\n').map(l=>l.trim()).includes(target) && el.offsetHeight > 0);
                if (el) {{ el.click(); return true; }}
                return false;
            }}''', chat_name)
            
        # 5. Profile Bridge
        chat_btn = page.locator('button:has-text("Chat"), button:has-text("聊天"), [role="button"]:has-text("Chat")').first
        if await chat_btn.is_visible():
            await chat_btn.click()
            await asyncio.sleep(1)
        
        # 6. Verification
        header_locator = page.locator(CHATROOM_HEADER_SELECTOR).first
        input_area = page.locator(MESSAGE_INPUT_SELECTOR).first
        
        if await header_locator.is_visible():
            if (await header_locator.inner_text()).strip() == chat_name:
                return {"status": "success", "chat_name": chat_name}
        
        if await input_area.is_visible():
            return {"status": "success", "chat_name": chat_name}

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
