# Snap Chromium Singleton Lock Management

## Symptoms of Lock Issues
- `Failed to create /path/to/SingletonLock: Permission denied (13)`: Caused by choosing a directory outside `~/snap/chromium/common/`.
- `chrome-error://chromewebdata/`: Often a result of AppArmor blocking navigation or profile access.

## Extraction Logic
To find which process owns a lock without blind-killing:
```bash
LOCK_FILE="$USER_DATA_DIR/SingletonLock"
if [ -L "$LOCK_FILE" ]; then
    LOCK_INFO=$(readlink "$LOCK_FILE")
    # Format is usually: hostname-pid
    LOCK_PID=$(echo $LOCK_INFO | cut -d'-' -f2)
    ps -p $LOCK_PID -o comm=,args=
fi
```

## User Preference: Error over Silence
- **Always report** the conflicting PID rather than `pkill`.
- **Verify state** before starting. Use `lsof -Pi :$PORT -sTCP:LISTEN -t` to check if the debugging port is already held by a ghost process.
