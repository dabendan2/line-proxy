#!/bin/bash
# scripts/start_persistent_line.sh
# Starts a persistent headful Chromium with LINE extension and CDP enabled in Xvfb.

PORT=${1:-9222}
USER_DATA_DIR=${2:-/tmp/line_persistent_session}
EXT_ID="ophjlpahpchlmihnnnihgmmeilfjmjjc"
EXT_PATH="/home/ubuntu/snap/chromium/common/chromium/Default/Extensions/$EXT_ID/3.7.2_0"

pkill -f chromium || true
rm -f "$USER_DATA_DIR/SingletonLock"
mkdir -p "$USER_DATA_DIR"

echo "Starting Persistent LINE Browser on port $PORT..."
xvfb-run -a chromium-browser \
    --remote-debugging-port=$PORT \
    --user-data-dir="$USER_DATA_DIR" \
    --no-sandbox \
    --disable-setuid-sandbox \
    --disable-extensions-except="$EXT_PATH" \
    --load-extension="$EXT_PATH" \
    --no-first-run \
    --no-default-browser-check \
    --disable-dev-shm-usage \
    --window-size=1280,720 \
    &

sleep 5
curl -s "http://localhost:$PORT/json/version" && echo -e "\nBrowser is ready."
