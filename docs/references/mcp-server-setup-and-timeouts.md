# MCP Server Setup & Timeout Management

## 1. Installation on Externally Managed Environments
In environments where `pip install` is blocked by PEP 668 (e.g., modern Ubuntu/Debian), use the `--break-system-packages` flag for the `mcp` SDK if a virtual environment is not feasible for the global agent:
```bash
pip install mcp --break-system-packages
```

## 2. Ad-hoc Configuration with mcporter
To use the `line-proxy` MCP server without restarting the Hermes Agent (required for `config.yaml` updates), register it with `mcporter`:
```bash
mcporter config add line_proxy \
  --command "/home/ubuntu/line-proxy/venv/bin/python3" \
  --arg "/home/ubuntu/line-proxy/src/mcp_server.py"
```
Call tools via:
```bash
mcporter call line_proxy.prepare_line_instance --config /home/ubuntu/line-proxy/config/mcporter.json
```

## 3. Handling start_proxy_task Timeouts
The `start_proxy_task` tool runs a multi-turn agent loop which frequently exceeds the default 60s MCP/Terminal timeout.
- **Symptom**: `[Command timed out after 60s]` or `mcporter` returning an empty response.
- **Workaround**: If the task is simple (e.g., "send hello"), use a direct Playwright script instead of the full Proxy Engine to avoid the overhead.
- **Reference Script**: `/tmp/send_line_hello.py` (or similar ad-hoc scripts) can bypass the engine for one-off actions.

## 4. Model Availability Pitfalls
The `google-genai` SDK used in the engine defaults to specific model strings. If you see `404 NOT_FOUND` for models like `gemini-2.0-flash-exp` in logs:
1. Verify the model name via `ListModels` in the Google AI Studio console.
2. Ensure the `GOOGLE_API_KEY` is correctly propagated in the MCP server's environment.
3. Use `gemini-1.5-flash` or current stable versions; avoid experimental strings that may be deprecated or moved between API versions (v1 vs v1beta).
