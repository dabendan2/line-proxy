# SDK & Model Availability Pitfalls

## 404 NOT_FOUND Errors
When using the `google-genai` Python SDK with the LINE proxy framework, you may encounter 404 errors for specific models:
- **Error**: `404 NOT_FOUND. {'error': {'code': 404, 'message': 'models/gemini-2.0-flash-exp is not found for API version v1beta...'}}`
- **Cause**: The SDK version or the specific service account/API key configuration might not have access to the `v1beta` endpoint for that model name in the way the SDK requests it.

### Verified Stable Models
- `gemini-flash-latest`
- `gemini-3-flash-preview`
- `gemini-pro-latest`

### Troubleshooting Steps
1. Run a model list check:
   ```python
   from google import genai
   client = genai.Client(api_key=...)
   for m in client.models.list():
       print(m.name)
   ```
2. If the desired model is missing from the list, it cannot be used with the current credentials/SDK.
3. Use the literal name returned by `list()` (e.g., `models/gemini-flash-latest`) or its short alias.

## Redundant Environment Variables
- **Pitfall**: Manually `export`ing `GOOGLE_API_KEY` in every `terminal` call.
- **Correction**: The `src/line_proxy.run_task (MCP)` script includes:
  ```python
  env_path = Path.home() / ".hermes" / ".env"
  if env_path.exists():
      load_dotenv(dotenv_path=env_path)
  ```
- **Action**: Trust the internal loader. Keep terminal commands clean.
