# Case Study: Bank Record Extraction & Sync Limits

## Background
User requested extraction of deposit records from a banking official account (CTBC).

## Technical Findings
1. **Layout Trap**: The chat window used `column-reverse`. Initial attempts to scroll to the "top" using `scrollTop = 0` failed because `0` was the bottom (newest). 
   - **Correction**: Use negative `scrollTop` values to navigate into the past.
2. **Synchronization Disparity**: The user had a record on 4/24 visible on mobile (screenshot proven), but the Chrome Extension refused to load history earlier than 4/29.
   - **Lesson**: If `scrollHeight` stops increasing during a negative scroll, the Extension's local sync limit has been reached. Do not keep scrolling; inform the user of the sync limit.
3. **Data Retrieval**:
   - **Previews**: `[data-message-content]` attributes are highly reliable for quick scans.
   - **Flex Messages**: Use Shadow DOM traversal for the actual details inside `flex-renderer`.

## User Style Preference
- **Conciseness**: Keep replies short.
- **Identity**: Always state "我是俊羽的 AI 代理人 Hermes".
- **Politeness**: Maintain respectful Traditional Chinese phrasing.
