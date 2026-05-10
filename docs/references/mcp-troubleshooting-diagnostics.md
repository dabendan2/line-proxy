# MCP Tool Discovery and Environment Troubleshooting (LINE Proxy)

## Symptom: MCP Tools Missing
Even if `line_proxy` is listed as enabled in `hermes mcp list`, the tools (`mcp_line_proxy_...`) may not appear in the agent's available tools.

## Common Causes
1. **Environment Variable Missing**: The MCP server (FastMCP) may fail to register tools if critical environment variables (like `GOOGLE_API_KEY`) are missing at startup, especially if the script has validation logic in the tool definitions.
2. **Config Path Mismatch**: The `config.yaml` might point to a path that doesn't exist or isn't executable in the current environment.

## Diagnostic Steps
1. **Check MCP List**:
   ```bash
   hermes mcp list
   ```
2. **Verify .env Load Path**: The `line-proxy` MCP server specifically looks for `~/.hermes/.env`. Verify its existence:
   ```bash
   ls -a ~/.hermes/.env
   ```
3. **Manual Execution Check**: Run the server script directly to see if it crashes or prints errors:
   ```bash
   /home/ubuntu/line-proxy/venv/bin/python3 /home/ubuntu/line-proxy/src/mcp_server.py
   ```
4. **Tool Verification via JSON-RPC**: Send a raw JSON-RPC request to the server via stdin to verify tool execution:
   ```bash
   /home/ubuntu/line-proxy/venv/bin/python3 /home/ubuntu/line-proxy/src/mcp_server.py <<EOF
   {
     "method": "tools/list",
     "params": {}
   }
   EOF
   ```

## Lessons Learned (Session 2026-05-11)
- **Do not fallback to `execute_code` too early**. If the user expects "Fast Preparation", take 10 seconds to diagnose why MCP is missing rather than writing a 50-line Playwright script that replicates existing MCP logic.
- **Shadow DOM is non-negotiable**. Any custom script *must* use the recursive walker pattern found in `scripts/find_line_contact.js` to be reliable.
