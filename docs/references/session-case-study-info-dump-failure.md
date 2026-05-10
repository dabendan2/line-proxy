# Case Study: Information Dump & Log Misinterpretation (2026-05-11)

## Context
The user requested a restaurant booking. The agent encountered stale `404 NOT_FOUND` errors in the logs and attempted to "fix" the problem by manual intervention.

## Failures

### 1. The "Information Dump" Error
- **Action**: The agent sent a single message containing Date, Time, People, Baby Cutlery, Parking, Name, and Phone.
- **Violation**: Broke the "Incremental Disclosure" and "< 40 words" rules.
- **Lesson**: Never use `send_line_message` to bypass the AI's step-by-step logic. The agent is a *proxy*, not a form-filler.

### 2. Ghost Debugging (Stale Logs)
- **Action**: Agent saw `404 NOT_FOUND` for Gemini models and switched the config.
- **Root Cause**: The error was from 12+ hours prior. The agent failed to verify the timestamp.
- **Lesson**: Logs must be cleared before a new run (`> logfile`). Timestamps are the first thing to check.

### 3. Improper Kickstart
- **Action**: Agent used `send_line_message` to "prime" the conversation because the last state was `ENDED`.
- **Error**: Included the business data in the prime message.
- **Lesson**: A kickstart should be a greeting only. The business data belongs inside the `run_task` loop.
