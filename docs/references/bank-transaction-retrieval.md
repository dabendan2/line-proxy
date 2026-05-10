# Bank Transaction Retrieval (LINE Agent Proxy)

This reference outlines the workflow for extracting banking records (like CTBC/中國信託) from a LINE chat.

## Data Structure
Bank notifications in LINE (Official Accounts) are typically sent as **Flex Messages**. 
- **The Challenge**: These messages are rendered in a **Shadow DOM** (`<flex-renderer>`).
- **The Clue**: The attribute `data-message-content` on the container `div` usually contains a high-level summary (e.g., `🔔即時入帳通知🔔`).

## Workflow

1.  **Search**: Search for the official account name (e.g., "中國信託").
2.  **Navigation**: Click the contact and wait for the chat to load.
3.  **Shadow DOM Traversal**: Use the `extract_flex_messages.py` script to bypass the Shadow DOM barrier and pull raw text from the `flex-renderer`.
4.  **Parsing**: Use RegEx to extract specific fields:
    - **Amount**: `新臺幣\s*([\d,]+)\s*元`
    - **Time**: `\d{4}/\d{2}/\d{2}\s*\d{2}:\d{2}:\d{2}`
    - **Type**: Look for keywords like `入帳`, `扣款`, `消費`.

## Example (CTBC Pattern)
> `🔔即時入帳通知🔔 新臺幣9,635元 入帳時間：2026/05/02 10:15:52 入帳帳號後四碼：6081`

## Pitfalls
- **Rich Menus**: Some banks put transaction buttons in a "Rich Menu" (at the bottom). If the message list is empty, try to detect the `RichMenu_button` and click to expand options.
- **Lazy Loading**: Older records may require `page.mouse.wheel(0, -5000)` to trigger history loading.
