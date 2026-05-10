# Case Study: Number Guessing Game Failures

## The "Dumb Bot" Trap
In this session, the agent used a regex-based background script (`monitor_game.py`) to handle a simple guessing game. 

### Failure Points:
1. **Language Fragility**: The script used `re.findall(r'\d+', msg)` which failed on Chinese numbers ("四百五十").
2. **Logic Loop**: Because the script failed to extract a number, it fell back to a default "Please enter a number" prompt.
3. **Collision**: When the user corrected the agent manually, the background script was still running and sent a "dumb" prompt immediately after the agent's manual apology, destroying the "Hermes" persona.
4. **DOM Misinterpretation**: Initially, the script looked at the *last* element of the message list. In LINE Extension's `column-reverse` layout, the *first* element (Index 0) is often the newest.

### Corrective Action for Future Agents:
- **Prioritize LLM for Logic**: For games or complex input, don't use regex scripts. Use the LLM to parse the message text to handle variants like "四百五十", "4 5 0", or "Is it four hundred?".
- **Kill Polling on Manual Intervene**: As soon as the user expresses frustration or asks a meta-question ("Are you a bot?"), kill all background processes and switch to 100% manual Hermes-persona chat.
- **Visual Double-Check**: Use `vision_analyze` to confirm who sent the last message and what the screen actually looks like before claiming "I have replied."
