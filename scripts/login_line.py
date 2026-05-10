import asyncio
from playwright.async_api import async_playwright
import os
import sys

async def login_line(email, password, extension_path, user_data_dir="/tmp/line_user_data"):
    async with async_playwright() as p:
        # Note: headless=True in Playwright 1.29+ (the "new" headless) supports extensions
        # But headless=False + xvfb-run is often more reliable for visual debugging.
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
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
            await asyncio.sleep(10) # Wait for UI
            
            # Find the active frame (Login is usually in a sandbox iframe)
            target = page
            for frame in page.frames:
                if "login" in frame.url or "auth" in frame.url:
                    target = frame
                    break
            
            # Form Filling with Keyboard Emulation (More resilient to bot detection)
            email_field = await target.wait_for_selector("input[type='email'], input[type='text']")
            password_field = await target.wait_for_selector("input[type='password']")
            
            if email_field and password_field:
                await email_field.fill(email)
                await password_field.fill(password)
                
                # Try clicking login button or pressing Enter
                login_btn = await target.query_selector("button:has-text('Log in'), button.btn_login, .login_btn, button[type='submit']")
                if login_btn:
                    await login_btn.click()
                else:
                    await password_field.press("Enter")
                
                print("Waiting for MFA/Verification screen (12s)...")
                await asyncio.sleep(12)
                
                # Success/Failure Detection
                # Check for verification code in all frames
                code = None
                for frame in page.frames:
                    code_el = await frame.query_selector(".verification_code, .code, .mfa_code, div[class*='code']")
                    if code_el:
                        code = await code_el.inner_text()
                        if code and len(code.strip()) >= 4:
                            code = code.strip()
                            break
                
                if code:
                    print(f"STATUS:MFA_REQUIRED CODE:{code}")
                elif "search" in (await page.content()).lower():
                    print("STATUS:SUCCESS")
                else:
                    print("STATUS:UNKNOWN_CHECK_SCREENSHOT")
                
                await page.screenshot(path="line_final_state.png")
            else:
                print("STATUS:FIELDS_NOT_FOUND")
                
        except Exception as e:
            print(f"ERROR:{e}")
        finally:
            await browser_context.close()

if __name__ == "__main__":
    # Usage: python3 login_line.py <email> <password> <ext_path>
    if len(sys.argv) < 4:
        print("Usage: python3 login_line.py <email> <password> <extension_path>")
    else:
        asyncio.run(login_line(sys.argv[1], sys.argv[2], sys.argv[3]))
