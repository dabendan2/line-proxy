# Case Study: dabendan.test Search Failure

## Context
During a session to review the `dabendan.test` chat, the agent encountered a situation where the browser was already open to a different chat (`丸俊文`). A standard Playwright search and click approach failed.

## Failure Mode
1. **Selector Timeout**: `page.locator('[class*="searchResultItem-module__name"]', has_text="dabendan.test")` was found but `click()` timed out (30,000ms).
2. **Shadow DOM Depth**: The LINE Extension uses multiple layers of Shadow DOM. Standard click actions might not bubble correctly or the element might be obscured by the search result container's own shadow root.

## Success Resolution
1. **Two-Stage Injection**: Using `page.evaluate` to fill the search box ensured the search results were triggered.
2. **Recursive JS Finder**: Executing `find_line_contact.js` (which uses `createTreeWalker` to traverse `shadowRoot` recursively) successfully identified the clickable element.
3. **Profile Overlay Handling**: The JS script also handled the "Chat" button check, which appears if clicking the contact opens a profile card instead of a direct chat.

## Lessons
- Always fall back to `src/find_line_contact.js` for selection if standard locators fail.
- `connect_over_cdp` is the most reliable way to interact with a user's running LINE instance without triggering lock errors.
