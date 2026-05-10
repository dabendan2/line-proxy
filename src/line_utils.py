import asyncio
from playwright.async_api import async_playwright

async def get_line_page(context):
    """Finds the active LINE Extension page."""
    for page in context.pages:
        if "ophjlpahpchlmihnnnihgmmeilfjmjjc" in page.url:
            return page
    return None

HERMES_PREFIX = "[Hermes]"

async def extract_messages(page):
    script = f"""
    () => {{
        const results = [];
        const prefix = "{HERMES_PREFIX}";
        const items = document.querySelectorAll('.message-module__content_inner__j-iko, [class*="message_content"], [class*="bubble"]');
        items.forEach(msg => {{
            const clone = msg.cloneNode(true);
            const meta = clone.querySelectorAll('[class*="metaInfo"], [class*="time"], [class*="Read"]');
            meta.forEach(m => m.remove());
            
            let textEl = clone.innerText.trim();
            textEl = textEl.replace(/\\s*(Read|\\d+:\\d+\\s*(AM|PM|上午|下午))\\s*$/i, "").trim();
            
            if (textEl) {{
                const isSelfByPrefix = textEl.startsWith(prefix);
                const isSelfByDom = msg.closest('.mdNM08MsgSelf') !== null || 
                                   msg.closest('[class*="Self"]') !== null;

                results.push({{
                    text: textEl.replace(prefix, "").trim(), // Hide prefix from engine's logic
                    is_self_dom: isSelfByPrefix || isSelfByDom,
                    has_hermes_prefix: isSelfByPrefix
                }});
            }}
        }});
        return results;
    }}
    """
    try:
        data = await page.evaluate(script)
        return data if data else []
    except Exception as e:
        print(f"Extraction Error: {e}")
        return []

async def send_message(page, text):
    message_area = page.locator('.message_input, [contenteditable="true"], textarea').first
    await message_area.click()
    
    # Append the visible prefix
    prefixed_text = HERMES_PREFIX + " " + text
    
    await message_area.fill(prefixed_text)
    await page.keyboard.press("Enter")
