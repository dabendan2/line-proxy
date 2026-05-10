# Pitfall: Infinite Loop via Wrong Message Indexing

## Symptom
The LINE Proxy agent sends the same message repeatedly or loops through the same logic every 5 seconds without ever exiting, even if no new messages are received from the other party.

## Root Cause
In `engine.py`, the logic for checking `is_new` message depends on comparing the latest extracted message with `self.state["last_processed_msg"]`.

If `extract_messages` returns an array where **Index 0** is the **Oldest** message (Chronological order), then:
- `latest = msgs[-1]` correctly gets the newest message.
- However, if the code updates state using `self.state["last_processed_msg"] = latest_msgs[0]`, it is saving the **Oldest** message as the "last processed" anchor.

On the next loop:
- `msgs[-1]` (Newest) will NOT match `self.state["last_processed_msg"]` (Oldest).
- `is_new` becomes `True`.
- The engine triggers `generate_and_send_reply` again.

## Solution
Always use `msgs[-1]` to anchor the "last processed" state when the extraction order is chronological (Oldest First).

```python
# Correct Implementation
latest_msgs = await line_utils.extract_messages(self.page)
if latest_msgs:
    self.state["last_processed_msg"] = latest_msgs[-1].get("text", "")
```
