import asyncio
import sys
from playwright.async_api import async_playwright

async def check_cdp(port=9222):
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")
            print(f"✅ Successfully connected to CDP on port {port}")
            context = browser.contexts[0]
            print(f"Contexts: {len(browser.contexts)}")
            print(f"Pages: {len(context.pages)}")
            for i, page in enumerate(context.pages):
                title = await page.title()
                url = await page.url()
                print(f"  Page {i}: [{title}] {url}")
            await browser.close()
        except Exception as e:
            print(f"❌ Failed to connect to CDP: {e}")
            sys.exit(1)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9222
    asyncio.run(check_cdp(port))
