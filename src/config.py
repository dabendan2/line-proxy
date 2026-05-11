import os
from pathlib import Path

# Paths
BASE_DIR = Path("/home/ubuntu/line-proxy")
DATA_DIR = Path.home() / ".line-proxy"
LOG_DIR = DATA_DIR / "logs"
SCREENSHOT_DIR = DATA_DIR
ENV_PATH = Path.home() / ".hermes" / ".env"

# Browser Configuration
CDP_PORT = 9222
DEFAULT_PROFILE = "line_booking_session"
EXTENSION_ID = "ophjlpahpchlmihnnnihgmmeilfjmjjc"
VIEWPORT_WIDTH = 1600
VIEWPORT_HEIGHT = 1000

# AI Configuration
DEFAULT_MODEL = "gemini-3-flash-preview"
HERMES_PREFIX = "[Hermes]"
INTRO_PHRASE = "您好，我是 俊羽 的AI代理 Hermes。"

# Timing and Timeouts
SEARCH_TIMEOUT = 10000
POLL_INTERVAL = 5
AGENT_INPUT_WAIT = 120
CONVERSATION_END_WAIT = 120
TOOL_WAIT = 60
HERMES_API_URL = os.environ.get("HERMES_API_URL", "http://127.0.0.1:8642")

# Runtime Timeout: 50 minutes (3000 seconds)
RUNTIME_TIMEOUT = int(os.environ.get("LINE_ENGINE_RUNTIME_TIMEOUT", 3000))

# DOM Selectors
SEARCH_INPUT_SELECTOR = "input[placeholder*='Search'], input[placeholder*='搜尋'], .search_input, input[type='text']"
MESSAGE_INPUT_SELECTOR = '.message_input, [contenteditable="true"], textarea'
CHATROOM_HEADER_SELECTOR = '[class*="chatroomHeader-module__name"]'
CHATLIST_ITEM_TITLE_SELECTOR = '[class*="chatlistItem-module__title"]'
CHATLIST_ITEM_SELECTOR = 'xpath=ancestor::div[contains(@class, "chatlist_item")] | ancestor::button'

# Extraction Selectors
CHATROOM_CONTAINER_SELECTOR = '[class*="chatroom-module__chatroom"], [class*="message_list"]'
MESSAGE_ITEM_SELECTOR = '.message-module__message__7odk3, [class*="messageLayout-module__message"]'
MESSAGE_CONTENT_SELECTOR = '[class*="content_inner"], [class*="textMessageContent-module__text"]'
MESSAGE_TIME_SELECTOR = '[class*="time"], [class*="metaInfo-module__time"]'

# Ensure directories exist
os.makedirs(LOG_DIR, exist_ok=True)
