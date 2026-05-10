# Startup Takeover Deadlock Pitfall

## Symptom
When a LINE Proxy task is restarted (e.g., changing the task prompt or recovering from an error), the agent might enter a "silent wait" state where it does nothing, even though a response is needed.

## Root Cause
If the last message in the chat history was sent by the agent (Hermes) itself, the `while True` loop logic that checks for `is_new_message` will return `False` because the "latest" message matches the "last processed" message.

If the engine logic is `if is_new_message: generate_reply()`, and the agent was the last one to speak (e.g., "I will check with the user"), the agent will never trigger the initial `generate_reply()` upon restart because there is no *new* message from the user/store.

## Resolution: Forced Evaluation on Startup
The `engine.py` was patched to perform a **forced evaluation** immediately upon starting, regardless of whether a "new" message is detected.

```python
# In src/engine.py run()
self.state.update(self.history.rebuild_state(msgs, self.task_description))
# FORCED: Always evaluate once on startup to handle task pivots or restarts
await self.generate_and_send_reply(msgs)

while True:
    # Standard polling loop continues...
```

This ensures that if the task description has changed (e.g., from "Book 5/11" to "Ask for 5/13"), the agent will act on that new instruction immediately instead of waiting for a message that might never come.
