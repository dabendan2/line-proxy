import asyncio
import json
import sys
from playwright.async_api import async_playwright

async def cleanup():
    async with async_playwright() as p:
        try:
            # Connect to existing browser
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            pages = context.pages
            
            line_pages = [p for p in pages if "chrome-extension://" in p.url]
            error_pages = [p for p in pages if "chrome-error://" in p.url or "about:blank" in p.url]
            
            # 1. Close error pages
            for p_err in error_pages:
                await p_err.close()
                
            # 2. Consolidate LINE pages: Keep only the FIRST one
            closed_count = 0
            if len(line_pages) > 1:
                # We sort to try and keep the most "stable" one or just the first created
                for p_extra in line_pages[1:]:
                    await p_extra.close()
                    closed_count += 1
            
            # 3. If NO line pages exist (extreme case), don't open here (might be intentional logout)
            # but usually you'd want at least one.
            
            print(json.dumps({
                "status": "success",
                "closed_error": len(error_pages),
                "closed_extra_line": closed_count,
                "remaining_line_pages": max(0, len(line_pages) - closed_count)
            }))
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}))

if __name__ == "__main__":
    asyncio.run(cleanup())
