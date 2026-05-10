# LINE 1A2B Game Bot Pattern

This pattern allows the agent to play a state-driven 1A2B game via the LINE extension.

## Components
1. **Solver (`1a2b_solver.py`)**: A pure-logic module that filters 4-digit permutations based on history.
2. **State (`1a2b_state.json`)**: Tracks `history` (list of `[guess, a, b]`), `last_processed_msg`, and `game_over` flag.
### Bot Script
   - **Connection**: Connects via CDP (`connect_over_cdp`) to keep the browser instance alive.
   - **Targeting**: Use `await page.keyboard.press("Control+2")` to switch to Chats tab, then search for the contact.
   - **Scraping**: Check messages from NEWEST to oldest (Index 0 first).
   - **Interaction**:
     - **Error Handling**: Detect impossible scores (e.g., "5A" in a 4-digit game) or invalid sums (A+B > 4).
     - **Persona**: Use the "Hermes" persona (witty/agentic) to handle human jokes or complaints about speed.
   - **Logic**: Use the solver to filter combinations. If 4A is achieved, set `game_over: true`.

## Solver Logic (Boilerplate)
```python
import itertools

def get_ab(guess, target):
    a, b = 0, 0
    for i in range(len(guess)):
        if guess[i] == target[i]: a += 1
        elif guess[i] in target: b += 1
    return a, b

def solve_next(history):
    possible = ["".join(p) for p in itertools.permutations("0123456789", 4)]
    for prev_guess, a, b in history:
        possible = [n for n in possible if get_ab(prev_guess, n) == (a, b)]
    return (possible[0], len(possible)) if possible else (None, 0)
```

## Persistent CDP Advantage
Using CDP ensures the 1A2B bot can be run repeatedly (e.g., via cron) without triggering a logout or requiring a new MFA code, as long as the background Chromium process remains active.
