# Refactoring Scripts to MCP for LINE Automation

Transitioning from standalone bash/python scripts to a Model Context Protocol (MCP) server provides several benefits for persistent agents:
1. **Tool-based Interaction**: The agent can "call" a tool to find a chat instead of manually typing code to do it.
2. **State Management**: The MCP server can maintain an internal `BrowserManager` instance to track port usage and locks.
3. **Atomic Operations**: Discrete steps (Prepare -> Find -> Execute Task) reduce the complexity of individual tool calls.

## Transition Checklist

### 1. Identify "Tool-able" Blocks
In `line-proxy`, the logic was split into:
- **`prepare_line_instance`**: Handling the OS-level Chromium process.
- **`find_chat`**: Handling the extension-level navigation and Shadow DOM search.
- **`start_proxy_task`**: Handling the agentic loop (Gemini interaction).

### 2. Move Logic to Classes
Avoid global state. Create a `BrowserManager` for process control and keep `LineProxyEngine` for the agent loop. This makes the tools in `mcp_server.py` simple wrappers:

```python
@mcp.tool()
async def find_chat(chat_name: str, port: int = 9222):
    # Connect via CDP
    # Call Shadow DOM script
    # Verify result
    return status
```

### 3. Handle Timeouts
MCP tool calls have a default timeout (usually 120s). For tasks that may take longer (like a chat proxy), the tool should:
- Perform one full "turn" of the agent loop.
- Return the current status.
- Allow the calling agent to re-call the tool if the task is still `WAIT_FOR_USER_INPUT`.

### 4. Pass Environment Variables
MCP servers run in a filtered environment. Ensure API keys (`GEMINI_API_KEY`) are explicitly passed in the `env` section of the MCP configuration in `config.yaml` or `mcporter.json`.
