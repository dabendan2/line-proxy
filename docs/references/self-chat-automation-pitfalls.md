# Self-Chat Automation Pitfalls (LINE Extension)

When automating the LINE Chrome Extension in a "Self-chat" (Keep/Notes) or a chat where the agent is the only active participant, several unique challenges arise.

## 1. Identity Confusion (The "Mirror" Problem)
- **Symptom**: All messages in the DOM are marked as `reverse` (Self) regardless of who sent them (Hermes vs. User).
- **Pitfall**: The agent cannot rely on CSS classes (like `.mdNM08MsgSelf`) to distinguish its own messages from the user's input.
- **Solution 1: Content Matching**: Maintain a local state of `sent_messages` and check incoming text against this list.
- **Solution 2: Log-First Truth**: Read `~/.line-proxy/logs/` to identify messages explicitly marked as `SENT:`.
- **Solution 3: Physical Identity Anchor (Highly Recommended)**: In every outgoing message, prefix the text with `[Hermes]`. This makes identity independent of external logs. Even if logs are cleared, the script can re-scan the DOM and instantly recognize its own messages by the prefix.

## 2. Recursive Reply Loops
- **Symptom**: The agent replies to its own "Status Update" or "Identity Disclosure" messages.
- **Fix**: 
    - Use strict **Anchor Tracking** with timestamps.
    - Ensure the "New Message" trigger only fires on text that is *after* the anchor and *not* in the `sent_messages` or Log `SENT` buffer.

## 4. Anchor Drift
- **Symptom**: After a crash or restart, the agent processes old messages again.
- **Solution**: Always use `--anchor` and `--anchor-time` to hard-anchor the starting point of the session to the very last message currently in the chat.

    - If waiting for a human (e.g., "Wait for Chunyu's confirmation"), do **not** say "Goodbye". Instead, use "I'll get back to you later" or "Please wait a moment".
    - Only say "Goodbye" when the task is fully complete and the user has confirmed they are done.

## 4. The "Immediate Loop" (Post-Send Feedback)
- **Symptom**: In high-frequency polling (e.g. 5s), the agent sends a message and immediately (in the next poll cycle) reads its own message from the DOM, mistaking it for a "NEW MSG" before the script can update its local `last_processed` state.
- **Fix**: Immediately after calling `send_message`, the engine must:
    1.  Wait a brief moment (1s) for the UI to settle.
    2.  Extract the latest message from the DOM.
    3.  Force-update `last_processed_msg` and `sent_messages` with this content *before* yielding back to the main loop.
    4.  This ensures the next poll loop treats the message as "already seen" or "self-sent".
