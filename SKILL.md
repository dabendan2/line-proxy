---
name: line-proxy
description: Robust AI Proxy for LINE Chrome Extension with context preservation and smart takeover.
tags: [line, proxy, automation]
---

# LINE Proxy Engine

This is a robust AI-driven proxy system designed to represent the user in LINE conversations. It features smart identity detection, persistence, and unit testing.

## Key Features
- **Smart Takeover**: Automatically detects if the last message in a chat requires a response or if it should remain silent.
- **Identity Awareness**: Prioritizes local logs (`/tmp/line_proxy_*.log`) to distinguish between "Self" and "Other" messages, especially in Keep/Self-chat.
- **Context Filtering**: Uses `--last-ignored-msg` to define the historical boundary of a task.
- **Persistence**: Maintains state in JSON files to survive process restarts without redundant replies.

## Files
- `run.py`: CLI entry point.
- `engine.py`: Core logic and LLM integration.
- `line_utils.py`: Playwright-based LINE DOM manipulation.
- `etiquette.md`: Social norms and rule definitions.
- `tests/`: Unit tests for the takeover logic.

## Usage
```bash
python3 run.py --chat "Contact Name" --last-ignored-msg "Text" --task "Task details..."
```

## Maintenance
Run tests to verify logic:
```bash
python3 run_line_tests.py
```
