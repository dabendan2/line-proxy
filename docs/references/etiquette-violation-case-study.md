# Etiquette Violation Case Study: Information Dumping

## Bad Example (The "Dump")
**Task**: "Book 5/11 13:00, 2 adults, 2 kids, need tableware and parking. If no 13:00, ask for other times."
**Agent Response**: 
> "[Hermes] 您好，我是 Hermes 代理機器人。我想預約 5/11 13:00 的位置，共 2 大 2 小。需要 1 個兒童餐具，並希望能保留停車位。如果 13:00 沒位子，請詢問 5/11 當天還有哪些時段可以預約，謝謝！"

**Why it's bad**:
1. **Cognitive Overload**: The recipient has to process 4 different requirements plus a conditional logic in one bubble.
2. **Logic Leakage**: Telling the store the "backup plan" (asking for other times) weakens the negotiation and feels robotic.
3. **Bot-like Tone**: Long, multi-sentence paragraphs are rare in organic messaging.

## Good Example (Incremental Disclosure)
**Task**: (Same as above)
**Agent Message 1**: 
> "您好，我想預約 5/11 13:00 的位置，請問 2 大 2 小還有位子嗎？"

**Process**:
- Wait for "有的".
**Agent Message 2**:
> "好的，那再麻煩幫我準備 1 個兒童餐具，另外想請問當天方便保留停車位嗎？"

**Why it's good**:
1. **High Signal-to-Noise**: Each bubble requires only a simple "Yes/No" or "OK" from the recipient.
2. **Organic Flow**: Mimics how a human naturally confirms availability before listing requirements.
3. **Focus**: Prevents the store from missing one of the requirements in a wall of text.
