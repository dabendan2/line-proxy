# Manual MCP Initialization Pattern

When debugging or manually calling an MCP server from an agent environment where the standard toolset is missing or failing, use the `mcp` Python library for a robust connection.

## Why avoid Shell Pipes?
Using `echo '{"method": ...}' | python mcp_server.py` often fails because:
1.  **JSON Validation**: Multi-line strings in shell can break JSON formatting.
2.  **Initialization Order**: MCP servers require an `initialize` request/response handshake before accepting tool calls.
3.  **Standard Input/Output**: MCP is a stateful protocol over stdio; simple pipes don't handle the full lifecycle correctly.

## Recommended Python Pattern

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def call_mcp_tool():
    server_params = StdioServerParameters(
        command="/path/to/venv/bin/python3",
        args=["/path/to/mcp_server.py"],
        env=None # Add custom env if needed
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Mandatory handshake
            await session.initialize()
            
            # Call your tool
            result = await session.call_tool("your_tool_name", arguments={"key": "value"})
            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(call_mcp_tool())
```

## Application to Line-Proxy
This pattern was used to verify `prepare_line_instance` and `find_chat` when the agent's native MCP integration was stale.
