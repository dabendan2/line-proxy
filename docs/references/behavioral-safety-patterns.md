# LINE Proxy Behavioral Safety Patterns

Ensuring an AI agent doesn't sound "robotic" or "stuck in a loop" after a script restart or a context change.

## 1. Adaptive Introduction (自適應身分揭露)
**Problem**: The agent introduces itself ("I am Hermes...") every time the script starts, even if it's already in the middle of a conversation.
**Pattern**:
- Before generating a prompt, the engine scans the visible message history (`context_lines`).
- Search for identity anchors like `[Hermes]`, `AI代理`, or `Chunyu`.
- If found, the prompt instruction changes from "Introduce yourself" to "Continue naturally, DO NOT re-introduce yourself."

## 2. Silent Exit / Goodbye Protection (再見保護)
**Problem**: The user says "Goodbye" or "Thanks", the script restarts, sees "Last message is from user", and tries to generate a new reply like "How can I help you?".
**Pattern**:
- Prompt Instruction: "If both parties have said goodbye (e.g., 'Bye', 'Thanks', 'See ya') and the task is done, generate ZERO social reply. Output the `[END]` tag only."
- Implementation: In `engine.py`, if `reply_text` is empty but `reason` tag exists, skip `send_message`.

## 3. Restart Recovery Logic (重啟安全性)
**Problem**: Script crashes immediately after sending a message. Upon restart, it sees the last message is from the user (because it hasn't synced the sent one yet or the log is gone).
**Pattern**:
- **DOM Check**: The script MUST check the DOM before acting.
- If the latest message in the DOM has the `[Hermes]` prefix or the `Self` CSS class, set `startup_action_needed = False`.
- Use content deduplication: If `latest_text` equals any message in `sent_messages` buffer, ignore it.

## 4. Info Dumping Prevention (資訊傾倒防護)
**Problem**: The model wants to "be helpful" and gives all answers (time, name, phone, parking) at once.
**Pattern**:
- High-penalty instruction in `etiquette.md`: "ONE task per message. If they ask for 5 things, answer 1 or 2 and wait for acknowledgement."
- Verification: Unit tests using mocks to verify that a prompt asking for "Name & Phone" results in a reply only containing "Name" if phone isn't critical yet.
