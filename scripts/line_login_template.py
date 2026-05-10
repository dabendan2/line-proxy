import asyncio
from playwright.async_api import async_playwright
import os

async def login_line(email, password, user_data_dir="/tmp/line_user_data"):
    async with async_playwright() as p:
        # Snap path for Ubuntu Chromium
        extension_path = "/home/ubuntu/snap/chromium/common/chromium/Default/Extensions/ophjlpahpchlmihnnnihgmmeilfjmjjc/3.7.2_0"
        
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, # Extensions usually require headful or 'new' headless
            args=[
                f"--disable-extensions-except={extension_path}",
                f"--load-extension={extension_path}",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        
        page = await browser_context.new_page()
        try:
            print("Navigating to LINE extension...")
            await page.goto("chrome-extension://ophjlpahpchlmihnnnihgmmeilfjmjjc/index.html", timeout=60000)
            await asyncio.sleep(8)
            
            # Check for existing session or login UI in iframes
            target = page
            for frame in page.frames:
                if "login" in frame.url or "auth" in frame.url:
                    target = frame
                    break
            
            email_field = await target.query_selector("input[type='email'], input[type='text']")
            if email_field:
                password_field = await target.query_selector("input[type='password']")
                await email_field.fill(email)
                await password_field.fill(password)
                
                login_btn = await target.query_selector("button:has-text('Log in'), button.btn_login, .login_btn, button[type='submit']")
                if login_btn:
                    await login_btn.click()
                else:
                    await password_field.press("Enter")
                
                print("Login triggered. Check for 6-digit MFA code on screen.")
                await asyncio.sleep(10)
                await page.screenshot(path="line_mfa_check.png")
            else:
                print("Email field not found. Already logged in?")
                
            # Wait for dashboard
            for i in range(12): # Wait up to 60s for user to complete MFA
                content = await page.content()
                if "Chats" in content or "Friends" in content:
                    print("SUCCESS: Logged in to dashboard.")
                    return True
                await asyncio.sleep(5)
                
            print("TIMEOUT: Dashboard not detected.")
            return False
                
        except Exception as e:
            print(f"ERROR: {e}")
            return False
        finally:
            await browser_context.close()

if __name__ == "__main__":
    # Usage: python3 scripts/line_login_template.py
    asyncio.run(login_line("YOUR_EMAIL", "YOUR_PASSWORD"))
