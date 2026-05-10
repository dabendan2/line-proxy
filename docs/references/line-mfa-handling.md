# LINE MFA Handling

When automating LINE via the Chrome Extension, first-time logins or new IP addresses will trigger a 6-digit PC verification code.

## Detection Logic (Playwright)

```python
content = await page.content()
if "verification code" in content.lower() or "pc verification" in content.lower():
    # Attempt extraction via DOM
    code_el = await page.query_selector(".verification_code, .code, .pc_verification_code")
    if code_el:
        code = await code_el.inner_text()
    else:
        # Fallback to Regex on page text
        import re
        text = await page.inner_text("body")
        match = re.search(r"\b\d{6}\b", text)
        code = match.group(0) if match else "Unknown"
    
    print(f"MFA_CODE_ALERT:{code.strip()}")
```

## Vision Verification
If DOM extraction fails or code is unreadable via `inner_text` (e.g., rendered in a canvas or obfuscated), use `vision_analyze` on a screenshot:
- **Prompt:** "What is the 6-digit verification code shown on the screen?"
- **UI Marker:** The code is typically in a central white modal labeled "PC verification".
