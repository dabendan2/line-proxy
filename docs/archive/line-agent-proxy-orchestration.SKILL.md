---
name: line-agent-proxy-orchestration
description: "High-level logic for LINE Proxy. Redirects to central documentation in line-proxy project."
tags: [line, agent, proxy, automation]
---

# LINE Agent Proxy Orchestration (Gateway)

## ⚠️ Redirect: Centralized Documentation
The primary tool reference, calling conventions, maintenance protocols, and technical details are now centralized in the **LINE Proxy** project to ensure consistency.

**Primary Documentation Path**: `/home/ubuntu/line-proxy/SKILL.md`

### Key Navigation:
- **Calling Convention**: Use `line_proxy.run_task` via MCP (mcporter) as documented in the central LINE Proxy documentation.
- **Project Context**: Refer to the `line-proxy` project directory for infrastructure details.
- **Logs**: `~/.line-proxy/logs/{chat_name}.log`

### Technical Pitfalls:
- **Startup Deadlock**: See `references/startup-takeover-deadlock.md` for details on why the engine must perform a forced evaluation on startup.
- **Legacy Filenames**: `run.py` has been fully deprecated and replaced by `line_proxy.run_task (MCP)`. Global cleanup was performed on 2026-05-11.

### Interaction Guidelines (Permanent):
- **Identity**: Always introduce yourself as "您好，我是 俊羽 的AI代理 Hermes。"
- **Conciseness**: Keep LINE replies under 40 words.
- **Privacy**: Do not provide phone/name until booking availability is confirmed by the store.
- **Incremental Disclosure**: Ask for one piece of information at a time.
