# Pitfall: Shell Argument Word-Splitting with mcporter

When sending multi-line text or messages with spaces/newlines to LINE via `mcporter call line_proxy.send_line_message`, the default `key:value` syntax fails.

## The Error
If you run:
`mcporter call line_proxy.send_line_message chat_name:dabendan.test text:Hello World`
The shell sees:
1. `mcporter`
2. `call`
3. `line_proxy.send_line_message`
4. `chat_name:dabendan.test`
5. `text:Hello`
6. `World`

The MCP tool receives `text` as "Hello" and `World` as an extra unexpected positional argument.

## The Solution: JSON + shlex
Always use the `--args` flag with a JSON object and wrap the whole thing in `shlex.quote` (in Python) to ensure newlines and spaces are preserved and correctly passed as a single string to the MCP tool.

```python
import json, shlex
payload = {
    "chat_name": "dabendan.test",
    "text": "Board:\n1 | 2 | 3\n---------\n4 | X | 6"
}
# Correct way:
cmd = f"npx mcporter call line_proxy.send_line_message --args {shlex.quote(json.dumps(payload))}"
```
