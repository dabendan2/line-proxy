import asyncio
from config import EXTENSION_ID, HERMES_PREFIX, MESSAGE_INPUT_SELECTOR, CHATROOM_HEADER_SELECTOR, \
    CHATLIST_ITEM_TITLE_SELECTOR, CHATLIST_ITEM_SELECTOR, CHATROOM_CONTAINER_SELECTOR, \
    MESSAGE_ITEM_SELECTOR, MESSAGE_CONTENT_SELECTOR, MESSAGE_TIME_SELECTOR

async def get_line_page(context):
    """Finds the active LINE Extension page."""
    for page in context.pages:
        if EXTENSION_ID in page.url:
            return page
    return None

async def select_chat(page, chat_name):
    """Ensures the correct chat is selected in the UI using strict title matching."""
    try:
        # 1. Check current header first
        header_locator = page.locator(CHATROOM_HEADER_SELECTOR, has_text=chat_name).first
        if await header_locator.is_visible():
            text = await header_locator.inner_text()
            if text.strip() == chat_name:
                return {"status": "success", "info": f"Chat '{chat_name}' is already selected."}

        # 2. Strict search in sidebar: title must match EXACTLY
        title_locator = page.locator(CHATLIST_ITEM_TITLE_SELECTOR, has_text=chat_name)
        count = await title_locator.count()
        
        target_item = None
        for i in range(count):
            loc = title_locator.nth(i)
            text = await loc.inner_text()
            if text.strip() == chat_name:
                # Found the exact title. Get the clickable parent container
                target_item = loc.locator(CHATLIST_ITEM_SELECTOR).first
                break
        
        if target_item:
            await target_item.click()
            await asyncio.sleep(2)
            # Verify header
            header_text = await page.locator(CHATROOM_HEADER_SELECTOR).first.inner_text()
            if header_text.strip() == chat_name:
                return {"status": "success"}
            return {"status": "failed", "error": f"Header verification failed. Expected '{chat_name}', got '{header_text}'"}
        
        return {"status": "not_found", "error": f"Could not find chat with exact title '{chat_name}'"}

    except Exception as e:
        return {"status": "error", "error": str(e)}

async def extract_messages(page):
    script = f"""
    () => {{
        const results = [];
        const prefix = "{HERMES_PREFIX}";
        
        // Find the ACTIVE chatroom container
        const chatroom = document.querySelector('{CHATROOM_CONTAINER_SELECTOR}');
        if (!chatroom) return [];

        const items = Array.from(chatroom.querySelectorAll('{MESSAGE_ITEM_SELECTOR}'));
        items.forEach(msg => {{
            // Text extraction
            const contentEl = msg.querySelector('{MESSAGE_CONTENT_SELECTOR}');
            if (!contentEl) return;
            
            let text = contentEl.innerText.trim();
            
            // Timestamp extraction
            const timeEl = msg.querySelector('{MESSAGE_TIME_SELECTOR}');
            const timestamp = timeEl ? timeEl.innerText.trim() : "";
            
            const isSelfByPrefix = text.startsWith(prefix);
            const isSelfByDom = msg.classList.contains('mdNM08MsgSelf') || 
                               msg.getAttribute('class').includes('Self');

            results.push({{
                text: text.replace(prefix, "").trim(),
                is_self_dom: isSelfByPrefix || isSelfByDom,
                has_hermes_prefix: isSelfByPrefix,
                timestamp: timestamp
            }});
        }});
        
        // Ensure chronological order: older messages first
        return results.reverse();
    }}
    """
    try:
        data = await page.evaluate(script)
        return data if data else []
    except Exception as e:
        print(f"Extraction Error: {e}")
        return []

async def send_message(page, text):
    message_area = page.locator(MESSAGE_INPUT_SELECTOR).first
    await message_area.click()
    
    # Append the visible prefix
    prefixed_text = f"{HERMES_PREFIX} {text}"
    
    await message_area.fill(prefixed_text)
    await page.keyboard.press("Enter")
