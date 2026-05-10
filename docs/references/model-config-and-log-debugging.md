# LINE Proxy: Model Configuration & Log Debugging

## Model 404 Errors
If the `run_task` engine fails with `404 NOT_FOUND` for a model (e.g., `models/gemini-2.0-flash-exp` not found), it usually means the `DEFAULT_MODEL` in `src/config.py` is outdated or unavailable for the current API key.

### Verification
Run a simple script using the venv to check available models:
```python
from google import genai
client = genai.Client(api_key=...)
for m in client.models.list():
    print(m.name)
```

### Fix
Update `~/line-proxy/src/config.py`:
```python
# AI Configuration
DEFAULT_MODEL = "gemini-2.0-flash" # Use a verified available model
```

## Log Monitoring
The engine logs internal errors (like API failures) to:
`~/.line-proxy/logs/<chat_name>.log`

Always check this file if `run_task` starts but fails to send messages.

## Interaction Kickstarting
If a previous session ended with a `[Hermes]` message or an `EXPLICIT_ENDED` tag, the engine's takeover logic might not trigger a new response immediately. 
**Pattern**: Manually send the first task message using `send_line_message` before starting the background `run_task` to ensure the "latest message" is a fresh prompt for the AI.
