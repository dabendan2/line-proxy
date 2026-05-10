# LINE MFA / PC Verification Troubleshooting

## Symptoms & Identification
- **PC Verification Screen**: A modal titled "PC verification" appears after entering credentials. It instructs the user to "Enter the following code on your mobile device."
- **Verification Failure**: Red text "Verification failed on the mobile version of LINE. Please try again." appears if the code is rejected or expires.

## Extraction Technique
The 6-digit code is often difficult to target with CSS because it might be inside a closed Shadow DOM or a dynamic iframe.

**Recommended Extraction Logic:**
```python
# Try standard selectors first
code_el = await page.query_selector(".verification_code, .code, div[class*='code'], .pc_verification_code")
if not code_el:
    # Robust fallback: Regex on whole body text
    import re
    text = await page.inner_text("body")
    match = re.search(r"\b\d{6}\b", text)
    code = match.group(0) if match else "Unknown"
else:
    code = await code_el.inner_text()
```

## Troubleshooting Workflow
1. **Screenshot at T+5s**: Verify if the "PC Verification" modal is actually visible.
2. **Screenshot at T+20s**: Check if the modal transformed into an error message ("Verification failed...").
3. **MFA_CODE_ALERT**: Always print the code in a clear format (e.g., `MFA_CODE_ALERT:123456`) so monitoring tools or the user can see it immediately.
