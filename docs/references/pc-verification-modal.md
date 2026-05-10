# LINE PC Verification Modal

The "PC verification" modal appears during the login process when a new device/context is used or when security policies trigger a mandatory check.

## Visual Appearance
- **Title**: "PC verification" (or "電腦版驗證")
- **Message**: "As a security measure, you must verify your account when logging in via a PC for the first time. Enter the following code on your mobile device."
- **Code**: A large 6-digit numeric string (e.g., `710883`) displayed in the center.
- **Context**: The background is usually dimmed/masked.

## Automated Handling
1. **Wait**: Minimum 12 seconds after clicking "Log in".
2. **Scan Frames**: The modal is often inside a sandbox iframe (e.g., `ltsmSandbox.html`).
3. **Selector**: `.verification_code`, `div[class*='code']`.
4. **Fallback**: If `inner_text()` returns empty or the element is not found, take a screenshot of the 1600x1000 viewport. The code will be in the dead center.
5. **User Prompt**: "LINE 登入需要進行電腦版驗證，請在您的手機 LINE App 中輸入以下 6 位數驗證碼：[CODE]".
