# Deep Text Extractor for LINE Flex Messages

import asyncio
from playwright.async_api import async_playwright

async def extract_flex_text(page):
    """
    Recursively extracts text from all <flex-renderer> elements
    by traversing their Shadow DOM roots.
    """
    text_content = await page.evaluate('''() => {
        const getDeepText = (el) => {
            let text = "";
            if (el.shadowRoot) text += getDeepText(el.shadowRoot);
            for (const child of el.childNodes) {
                text += child.textContent + " ";
                if (child.nodeType === Node.ELEMENT_NODE) {
                    text += getDeepText(child);
                }
            }
            return text;
        };
        
        const renderers = document.querySelectorAll('flex-renderer');
        return Array.from(renderers).map(r => ({
            id: r.getAttribute('data-message-id'),
            text: getDeepText(r).replace(/\s+/g, ' ').strip()
        }));
    }''')
    return text_content
