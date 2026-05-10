# LINE Hangman Bot Pattern

The LINE Proxy can be used to host interactive games like Hangman (吊死鬼). 

## Implementation Strategy
- **Task Description**: Provide a clear multi-step task to the AI:
  1. Ask for permission to play.
  2. If accepted, announce the word length and complexity.
  3. Provide a fixed difficult word (e.g., `PNEUMONIA`).
  4. Display progress using an ASCII gallows and underscores (`_ _ _ _`).
  5. Update and reply after each letter input.
- **State Management**: The `HistoryManager` automatically tracks the board state in the chat history, so the AI knows which letters have been guessed.

## Example Task Prompt
"1. 詢問對方是否想玩 ASCII 吊死鬼遊戲（Hangman）。2. 如果對方同意，請告知：『太好了！我準備了一個非常難的單字（9個字母）。』並開始遊戲。3. 待猜單字為：PNEUMONIA。4. 請在對話中呈現 ASCII 吊架與進度（如 _ _ _ _ _ _ _ _ _）。5. 每次對方輸入一個字母後，更新狀態並回覆。"

## Pitfalls
- **Token Limits**: ASCII art can consume significant tokens. Keep the gallows simple.
- **Prefixes**: Ensure `[Hermes]` is added by the engine, not the LLM, to avoid double-prefixing or confusion.
- **Concurrency**: Use `PIDLock` to ensure only one instance of the game bot is running per chat.
