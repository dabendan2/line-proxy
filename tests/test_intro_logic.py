
import unittest
from unittest.mock import MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock config before importing engine
import config
config.INTRO_PHRASE = "Hello, I am Hermes AI Proxy."
config.OWNER_NAME = "Owner"
config.HERMES_PREFIX = "[Hermes]"

from engine import LineProxyEngine

class TestEngineIntro(unittest.TestCase):
    def setUp(self):
        self.page = MagicMock()
        self.chat_name = "test_chat"
        self.task = "test_task"
        # Mock HistoryManager
        self.history_patcher = unittest.mock.patch('engine.HistoryManager')
        self.mock_history_mgr = self.history_patcher.start()
        
        # Mock genai client
        self.genai_patcher = unittest.mock.patch('google.genai.Client')
        self.mock_genai = self.genai_patcher.start()
        
        # Mock open() for etiquette and prompt
        self.open_patcher = unittest.mock.patch('builtins.open', unittest.mock.mock_open(read_data="test prompt {{intro_instruction}}"))
        self.mock_open = self.open_patcher.start()

    def tearDown(self):
        self.history_patcher.stop()
        self.genai_patcher.stop()
        self.open_patcher.stop()

    def test_intro_needed_when_history_empty(self):
        engine = LineProxyEngine(self.page, self.chat_name, self.task)
        context = []
        prompt = engine._build_prompt(context)
        self.assertIn("這是你與對方的第一次對話。請務必先進行自我介紹", prompt)

    def test_intro_not_needed_when_intro_exists_recently(self):
        engine = LineProxyEngine(self.page, self.chat_name, self.task)
        context = [
            "[10:00 AM] Owner: Hi",
            "[10:01 AM] Hermes: Hello, I am Hermes AI Proxy. How can I help?"
        ]
        prompt = engine._build_prompt(context)
        self.assertIn("你已經在之前的對話中自我介紹過了", prompt)

    def test_intro_needed_when_hermes_talked_but_no_intro(self):
        engine = LineProxyEngine(self.page, self.chat_name, self.task)
        context = [
            "[10:00 AM] Owner: Hi",
            "[10:01 AM] Hermes: I am checking the weather."
        ]
        prompt = engine._build_prompt(context)
        # CURRENT BEHAVIOR: It should still intro because "AI代理" (or "AI Proxy") is missing
        self.assertIn("這是你與對方的第一次對話。請務必先進行自我介紹", prompt)

    def test_intro_needed_when_intro_is_too_old(self):
        # This is what the user likely wants. If the intro was 3 hours ago, 
        # and we are starting a new session, we should probably greet again.
        engine = LineProxyEngine(self.page, self.chat_name, self.task)
        context = [
            "[09:00 AM] Hermes: Hello, I am Hermes AI Proxy. How can I help?",
            "[09:05 AM] Owner: Ok thanks",
        ]
        # Add 10 more messages to push the intro out of the last 10
        for i in range(11):
            context.append(f"[10:{i:02d} AM] Owner: message {i}")
            
        # Now context has 13 messages, the intro is at index 0 (not in [-10:])
        prompt = engine._build_prompt(context)
        self.assertIn("這是你與對方的第一次對話。請務必先進行自我介紹", prompt)

if __name__ == '__main__':
    unittest.main()
