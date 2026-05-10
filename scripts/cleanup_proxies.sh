#!/bin/bash
# cleanup_proxies.sh
# 清理所有正在執行的 LINE 代理人進程，防止 Race Condition。

echo "Cleaning up background LINE proxy processes..."
pkill -f "run_engine.py --chat"
pkill -f "run_genai.py"

# 清理僵屍 Chromium 進程（若有需要）
# pkill -f "chromium-browser"

echo "Cleanup complete."
