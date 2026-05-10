# Self-Chat Identity & Reliability Pattern (Hermes)

In a "Self-Chat" environment (e.g., `dabendan.test` or talking to one's own business account), both incoming and outgoing messages may share the same CSS classes (like `.mdNM08MsgSelf`), making standard DOM-based identity extraction unreliable.

## The 3-Layer Solution

### 1. Physical Anchor (Prefixing)
- **Rule**: Every message sent by the AI must start with a distinct prefix, e.g., `[Hermes]`.
- **Extraction Logic**: When reading messages, any bubble starting with `[Hermes]` is treated as "Self" regardless of what the DOM says.

### 2. Temporal/Content Boundary (Boundary Line)
- **Problem**: On restart, the AI might see its own previous messages as "new input" if the history hasn't been synced or logs are cleared.
- **Solution**: Use `--last-ignored-msg`. This tells the engine: "Ignore everything up to this exact string." This creates a clean slate for the current task.

### 3. Process Isolation
- **Problem**: Zombie processes from failed runs or previous sessions can cause duplicate replies ("Echoing").
- **Action**: Always `pkill -f line_proxy.run_task (MCP)` (or the specific script name) before spawning a new background agent.

## Verification
- Use `vision_analyze` on a 1600x1000 screenshot to confirm the "last message" visible is indeed what the script thinks it is.
- Verify that `extract_messages` correctly filters out the prefix before sending text to the LLM.
