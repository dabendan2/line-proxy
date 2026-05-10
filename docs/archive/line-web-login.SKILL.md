---
name: line-web-login
description: Interactive login to LINE web version using email/password and mobile MFA. Documentation centralized in line-proxy.
tags: [line, login, browser, mfa]
---

# LINE Web Login (Centralized)

Expert techniques for logging into LINE services (Store, Developers, Extension).

## ⚠️ Redirect: Centralized Documentation
The primary methods for maintaining a persistent, logged-in state and the technical setup for the LINE extension are now centralized in the **LINE Proxy** project.

**Path**: `/home/ubuntu/line-proxy/SKILL.md`

## Key Concepts
- **Chat Access**: Official LINE chat on web is **only** available via the Chrome Extension (`ophjlpahpchlmihnnni`).
- **MFA Flow**: After email/password entry, a 4 or 6-digit code must be entered on the user's mobile device. Use `vision_analyze` to extract the code for the user.
- **Persistence**: Once logged in, the `line-proxy` system maintains the session via CDP on port 9222.

For technical details on Xvfb-run, Snap Chromium paths, and Shadow DOM scraping after login, refer to the `line-proxy/SKILL.md`.

## Workflow
1. Use `line_proxy.prepare_line_instance` to start the environment.
2. Perform login if needed (manual intervention required for MFA).
3. Handoff to `line_proxy.run_task` for automated tasks.
