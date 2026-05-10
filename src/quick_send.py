
import asyncio
from playwright.async_api import async_playwright
import sys

async def send_msg(chat_name, text):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] # 假設 LINE 分頁已開啟
        
        # 尋找對話框並傳送
        # (這裡簡化處理，直接呼叫 page.keyboard)
        await page.keyboard.type(text)
        await page.keyboard.press("Enter")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(send_msg(sys.argv[1], sys.argv[2]))
