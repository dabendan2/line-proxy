# Self-Chat Identity & Extraction

When running an automation script (like a game player) against a Hermes Proxy (acting as a GM) in the same chat room (e.g., `dabendan.test`), standard DOM-based identity checks (like `.mdNM08MsgSelf`) fail because *both* sides of the conversation are "Self" from the browser's perspective.

## Identity Disambiguation Strategies

1. **Content Cache (Sent List)**:
   Maintain a local list/set of exact strings sent by the *current script*.
   ```python
   sent_cache = set()
   # ... when sending ...
   sent_cache.add(text)
   # ... when extracting ...
   new_msgs = [m for m in all_msgs if m not in sent_cache]
   ```

2. **Log Rebuild (History Manager)**:
   Use the `~/.line-proxy/logs/` files which explicitly tag `SENT:` vs `NEW MSG:`. This is the most reliable "source of truth". If a script is starting mid-conversation, it must parse the last ~10 lines of the log to recover the current state.

3. **Message Indexing (The "Chronological Reversed" View)**:
   In the LINE Extension, `document.querySelectorAll('.message-module__content_inner__j-iko')` typically returns messages with **Index 0 as the newest**.
   - If the list is short, `reversed(msgs)` helps process them in chronological order.
   - If `msgs[0]` matches your last sent item, the bot hasn't replied yet.

4. **Visual Context**:
   Use `vision_analyze` to confirm if a message is on the left (Incoming) or right (Outgoing). Even in self-chat, "Incoming" messages from the proxy's perspective might appear as "Outgoing" in the DOM, but if the Proxy is running via the `line-proxy` engine, it will record them in the log.

## Pitfall: The "Echo" Loop
If a script extracts a message it *just* sent and interprets it as "User Input", it may trigger a recursive loop.
- **Solution**: Always deduplicate against the `sent_cache` AND the `last_processed_msg` ID/Text.
