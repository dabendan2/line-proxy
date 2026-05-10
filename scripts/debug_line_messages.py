import asyncio
from playwright.async_api import async_playwright
import sys

async def main():
    port = 9222
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            page = browser.contexts[0].pages[0]
            # Common selectors for LINE extension messages
            selectors = [
                "pre[class*='textMessageContent-module__text']",
                ".message",
                "[class*='message_text']"
            ]
            
            print(f"Connected to {page.url}")
            for selector in selectors:
                messages = await page.query_selector_all(selector)
                if messages:
                    print(f"\n--- Testing Selector: {selector} (Found {len(messages)}) ---")
                    for i, msg in enumerate(messages[:10]): # Show first 10
                        text = await msg.inner_text()
                        cls = await msg.get_attribute("class")
                        print(f"[{i}] {text[:50]}... (Class: {cls})")
            
            await browser.close()
        except Exception as e:
            print(f"Error connecting to CDP on port {port}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
