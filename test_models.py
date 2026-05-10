import os
from google import genai
from dotenv import load_dotenv
from pathlib import Path

ENV_PATH = Path.home() / ".hermes" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

try:
    for m in client.models.list():
        print(f"Model: {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
