#!/bin/bash
# scripts/start_line_snap.sh
# Standardized startup for LINE Extension in Snap-based Chromium with Lock Detection.

PORT=${1:-9230}
PROFILE_NAME=${2:-line_general_session}
USER_DATA_DIR="/home/ubuntu/snap/chromium/common/$PROFILE_NAME"
EXT_ID="ophjlpahpchlmihnnnihgmmeilfjmjjc"
EXT_PATH="/home/ubuntu/snap/chromium/common/chromium/Default/Extensions/$EXT_ID/3.7.2_0"

# 1. Check if Port is occupied
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    OCCUPIED_PID=$(lsof -t -i:$PORT)
    echo "ERROR: Port $PORT is already in use by PID $OCCUPIED_PID."
    echo "Please close the existing process or use reset_proxy.py."
    exit 1
fi

# 2. Check for SingletonLock
LOCK_FILE="$USER_DATA_DIR/SingletonLock"
if [ -L "$LOCK_FILE" ]; then
    LOCK_INFO=$(readlink "$LOCK_FILE")
    LOCK_PID=$(echo $LOCK_INFO | cut -d'-' -f2)
    
    if ps -p $LOCK_PID > /dev/null; then
        echo "ERROR: Profile is LOCKED by active PID: $LOCK_PID."
        exit 1
    else
        echo "Found stale SingletonLock. Removing..."
        rm -f "$LOCK_FILE"
    fi
fi

mkdir -p "$USER_DATA_DIR"

echo "Starting LINE Extension on Port $PORT (Profile: $PROFILE_NAME)..."
xvfb-run -a -s "-screen 0 1600x1000x24" chromium-browser \
    --remote-debugging-port=$PORT \
    --user-data-dir="$USER_DATA_DIR" \
    --no-sandbox \
    --disable-extensions-except="$EXT_PATH" \
    --load-extension="$EXT_PATH" \
    --no-first-run \
    --no-default-browser-check \
    --disable-dev-shm-usage \
    "chrome-extension://$EXT_ID/index.html" \
    &

# Wait for readiness
MAX_RETRIES=10
COUNT=0
while ! curl -s "http://localhost:$PORT/json/version" > /dev/null; do
    sleep 2
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "Error: Browser failed to start within 20s."
        exit 1
    fi
done

echo "LINE Extension is ready on port $PORT."
