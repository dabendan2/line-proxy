# Proactive Initiation Pattern for Proxy Agents

## Background
In previous versions of the `line-proxy` agent, the script would start in a "silent standby" mode if no new messages were detected immediately upon startup. This led to a bad user experience where the human had to initiate the conversation even if the AI was the one supposed to start (e.g., in a guess-the-number game).

## The Fix
The `HistoryManager.rebuild_state` logic was updated to differentiate between "Recovery" (restarting an ongoing task) and "Fresh Start" (a new task description).

### Logic Implementation (`history_manager.py`):
```python
if trusted_log:
    # ... logic for ongoing tasks ...
else:
    # Fresh run, no history in log: ALWAYS send an initial message/greeting
    state["startup_action_needed"] = True
    state["last_processed_msg"] = "___FRESH_TAKEOVER___"
```

## Why this matters
An AI Proxy should behave like a human taking over a desk. If you are told to "Start a game", you don't sit silently; you say "Hi, let's play". This proactive stance is now a core requirement for all Hermes Proxy tasks.

## Forbidden "AI-isms"
This session also identified that closures like "I'll go report to Chunyu" break immersion. The proxy should use human-like closures like "Cheers" or "Have a good one".
