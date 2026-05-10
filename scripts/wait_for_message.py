import asyncio
from playwright.async_api import async_playwright
import time
import sys

async def monitor():
    """
    Standard Watchdog script for LINE Extension.
    Exits with code 0 when a new message is detected compared to the baseline.
    """
    async with async_playwright() as p:
        try:
            # Connect to existing browser
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            # Find the LINE extension page
            page = next(p for p in context.pages if "ophjlpahpchlmihnnnihgmmeilfjmjjc/index.html" in p.url)
            
            # Baseline: The newest message currently visible (Index 0 in LINE DOM)
            last_msg = await page.evaluate("""
                () => {
                    const items = Array.from(document.querySelectorAll('span[data-message-content], .mdNM08MessageText, .message_text'));
                    return items.length > 0 ? items[0].innerText.trim() : "";
                }
            """)
            print(f"Monitoring starting. Baseline newest message: {last_msg}")
            
            # Poll every 3 seconds
            while True:
                current_msg = await page.evaluate("""
                    () => {
                        const items = Array.from(document.querySelectorAll('span[data-message-content], .mdNM08MessageText, .message_text'));
                        return items.length > 0 ? items[0].innerText.trim() : "";
                    }
                """)
                
                # Check for content change
                if current_msg != last_msg and len(current_msg) > 0:
                    print(f"NEW_MESSAGE_DETECTED: {current_msg}")
                    # Script terminates on discovery
                    break
                
                await asyncio.sleep(3)
        except Exception as e:
            print(f"Monitor Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(monitor())
