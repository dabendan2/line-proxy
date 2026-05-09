import asyncio
from playwright.async_api import async_playwright

async def get_line_page(context):
    """Finds the active LINE Extension page."""
    for page in context.pages:
        if "ophjlpahpchlmihnnnihgmmeilfjmjjc" in page.url:
            return page
    return None

async def extract_messages(page):
    script = """
    () => {
        const results = [];
        const items = document.querySelectorAll('.message-module__content_inner__j-iko, [class*="message_content"], [class*="bubble"]');
        items.forEach(msg => {
            const textEl = msg.innerText.trim();
            const timeEl = msg.parentElement.querySelector('[class*="metaInfo-module__meta"], [class*="time"]');
            
            if (textEl) {
                const isSelf = msg.closest('.mdNM08MsgSelf') !== null || 
                               msg.closest('[class*="Self"]') !== null ||
                               msg.parentElement.closest('[class*="Self"]') !== null ||
                               window.getComputedStyle(msg.parentElement).textAlign === 'right';

                results.push({
                    text: textEl,
                    time: timeEl ? timeEl.textContent.trim() : "",
                    is_self_dom: isSelf
                });
            }
        });
        // Newest at index 0
        return results;
    }
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
    await message_area.fill(text)
    await page.keyboard.press("Enter")
