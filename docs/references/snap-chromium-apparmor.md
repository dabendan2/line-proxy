# Snap Chromium & AppArmor Pitfalls

When running the LINE Extension in a Snap-based Chromium environment, several unique failures occur that differ from standard `.deb` or `google-chrome` installations.

## 1. SingletonLock Permission Denied
**Error:** `Failed to create /home/ubuntu/.line_persistent_session/SingletonLock: Permission denied (13)`
**Cause:** AppArmor prevents Snap Chromium from writing to hidden directories in `~` that are not under `~/snap/chromium`.
**Solution:** Always use a path under `~/snap/chromium/common/` (e.g., `~/snap/chromium/common/line_profile`).

## 2. DBus Access Denied
**Error:** `An AppArmor policy prevents this sender from sending this message to this recipient... interface="org.freedesktop.DBus" member="ListActivatableNames"`
**Context:** These logs appear in the terminal but are generally non-fatal for automation if the `--remote-debugging-port` is successfully opened.
**Solution:** Check `curl http://localhost:<port>/json/list` to verify readiness rather than relying on the absence of DBus errors.

## 3. Extension Pathing
**Location:** `/home/ubuntu/snap/chromium/common/chromium/Default/Extensions/ophjlpahpchlmihnnnihgmmeilfjmjjc/`
**Note:** Ensure you include the version-specific subdirectory (e.g., `3.7.2_0`) in `--load-extension` and `--disable-extensions-except`.

## 4. Port Selection
If multiple agents or sessions are running, Snap's lock management can get confused. If port 9222 remains "Failed to connect", try an alternate port like 9230.
