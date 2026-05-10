# LINE Extension Login Flow Diagnostics

This document records the patterns discovered for identifying the state of the LINE Chrome Extension during the login and MFA process.

## State Detection Patterns

### 1. Login Failure
- **Visual Signal**: Red border around input fields + red text.
- **Text**: "Email address or password is either incorrect or not registered with LINE."
- **Action**: Verify credentials. Do not attempt multiple times rapidly to avoid "Unable to log in at this time" errors.

### 2. PC Verification (MFA)
- **Visual Signal**: A modal titled "PC verification".
- **Content**: "As a security measure, you must verify your account... Enter the following code on your mobile device."
- **Code Extraction**: 6-digit bold numbers.
- **Critical Handling**: Do NOT restart the browser. This invalidates the code. Stay on the page.

### 3. Transition Stall
- **Symptom**: User completes MFA, but the screen stays on the login page or the verify modal doesn't disappear.
- **Solution**: Execute `page.reload()`. This often forces the session to pick up the authenticated state and redirect to `index.html#/`.

### 4. Successful Login Identification
- **DOM Indicators**: Presence of elements with `placeholder*="Search"` or classes like `.message_list`, `.mdNM08Message`.
- **URL Check**: The URL hash usually changes to `#/`.

## Known Issues
- **"Unable to log in at this time"**: Triggered by too many failed attempts or frequent session resets. If this occurs, wait 1-2 minutes and perform a full `page.reload()` before trying the password again.
