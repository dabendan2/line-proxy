# Log-as-State Architecture in Messaging Automation

When automating messaging platforms (LINE, WhatsApp, etc.), maintaining a persistent state is critical for surviving agent restarts and avoiding redundant replies.

## The Problem with JSON/DB State
- **Sync Issues**: If the agent crashes between sending a message and updating the DB, it may "forget" it sent the message and retry upon restart.
- **Identity Ambiguity**: Messaging DOMs (especially in Self-Chat or LINE Keep) often use identical classes for both parties, making it impossible to distinguish "Self" from "Other" solely through HTML.

## The Log-as-State Solution
Instead of a separate JSON/DB, the application log (`/tmp/line_proxy_<chat>.log`) is treated as the **Single Source of Truth**.

### 1. Unified Identity Logic
Every outgoing message is logged as `SENT: <text>`. Every incoming message is logged as `NEW MSG: <text>`.
- **Identity Recovery**: Upon restart, the engine parses the log. Messages under `SENT` are definitively attributed to the AI.
- **Seamless Recovery**: The engine checks the last line of the log. 
  - If last line == `SENT`: Status is "Waiting for other party". Silent startup.
  - If last line == `NEW MSG`: Status is "Need to respond". Immediate action.

### 2. Context Filtering (The "Last Ignored Message" Barrier)
To prevent the LLM from hallucinating or reprocessing ancient history, the engine uses a `--last-ignored-msg` barrier.
- Everything BEFORE this message (and the message itself) is discarded.
- Only messages AFTER this barrier (retrieved from DOM and supplemented by Logs) are fed into the prompt.

### 3. State Reconstitution
Variables like `sent_messages` and `exit_timers` are rebuilt dynamically from the log's timestamps and content. This eliminates stale state files and simplifies debugging (edit the log to fix the AI's memory).
