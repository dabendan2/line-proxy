import asyncio
from playwright.async_api import async_playwright
import os
import json
import re

# --- Core Logic ---
def get_ab(guess, target):
    a, b = 0, 0
    for i in range(len(guess)):
        if guess[i] == target[i]: a += 1
        elif guess[i] in target: b += 1
    return a, b

def solve_next(history):
    import itertools
    possible_numbers = ["".join(p) for p in itertools.permutations("0123456789", 4)]
    filtered = []
    for num in possible_numbers:
        match = True
        for prev_guess, a, b in history:
            pa, pb = get_ab(prev_guess, num)
            if pa != a or pb != b:
                match = False
                break
        if match: filtered.append(num)
    if not filtered: return None
    return filtered[0], len(filtered)

# --- Agent Class ---
class LineAgent:
    def __init__(self, contact_name, state_file):
        self.contact_name = contact_name
        self.state_file = state_file
        self.state = self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file): return json.load(f)
        return {
            "history": [], 
            "last_processed_msg": None, 
            "game_over": False, 
            "task": "1a2b",
            "current_interval": 1,
            "next_run_time": 0
        }

    async def run(self, cdp_url="http://localhost:9222"):
        import time
        now = time.time()
        if now < self.state.get("next_run_time", 0):
            print(f"Skipping run. Next check in {int(self.state['next_run_time'] - now)}s")
            return

        # ... (Connection logic) ...

        if incoming_msg != self.state["last_processed_msg"]:
            # New activity: Reset backoff
            self.state["current_interval"] = 1
            # ... (Process message) ...
        else:
            # No activity: Backoff (e.g., linear increase up to 10 mins)
            self.state["current_interval"] = min(10, self.state.get("current_interval", 1) + 1)
        
        self.state["next_run_time"] = now + (self.state["current_interval"] * 60)
        self.save_state()

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            # Find LINE tab
            page = None
            for context in browser.contexts:
                for p_page in context.pages:
                    if "ophjlpahpchlmihnnnihgmmeilfjmjjc" in p_page.url:
                        page = p_page
                        break
            
            if not page:
                print("LINE tab not found in CDP session.")
                return

            # Search contact
            search_box = await page.wait_for_selector("input[placeholder*='Search']", timeout=5000)
            await search_box.fill(self.contact_name)
            await asyncio.sleep(2)
            await (await page.query_selector(f"text='{self.contact_name}'")).click()
            await asyncio.sleep(2)

            # Read messages (Index 0 is Newest)
            messages = await page.query_selector_all(".message, [class*='message_text']")
            if not messages: return

            last_msg_text = await messages[-1].inner_text() # Adjust based on DOM order
            
            # Logic implementation for 1A2B
            if self.state["task"] == "1a2b" and not self.state["game_over"]:
                # ... (Logic from line_1a2b_bot_v3.py) ...
                pass
            
            await browser.close()
