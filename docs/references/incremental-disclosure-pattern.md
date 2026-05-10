# Incremental Disclosure Pattern for AI Proxies

## Problem
When an AI agent handles a task (e.g., booking a restaurant), it often has a list of requirements:
- Date & Time
- Number of people (Adults/Kids)
- Special requests (High chairs, Allergies)
- Logistics (Parking)
- Policy questions (Minimum spend)

Naive agents "dump" all this info in the first message. This is a high-signal "AI-ism" that users find annoying and unnatural.

## The Solution: Incremental Disclosure
1. **Primary Goal First**: Only state the core request (e.g., "I'd like to book for 5/11 at 1:00 PM for 5 people").
2. **Wait for Confirmation**: Wait for the human to confirm availability or ask questions.
3. **Lazy Requirement Injection**: Only inject secondary requirements (parking, cutlery) once the primary goal is secured or when logically appropriate in the flow.
4. **Contextual Pacing**: If the human asks a question (e.g., "What's your name?"), answer ONLY that question and perhaps one logical follow-up, but don't resume the "dump".

## Implementation in LINE Proxy
The `engine.py` should pass the entire "Source of Truth" (all requirements) to the LLM but use a system prompt (via `etiquette.txt`) that explicitly forbids multi-point inquiries.

### Example Bad Interaction
> **AI**: Hi, I want to book 5/11 13:00 for 2 adults 3 kids. I need a kids set, a parking space, and what is the minimum spend for kids?
> **Human**: ... (Confused/Annoyed)

### Example Good Interaction
> **AI**: Hi, I'd like to book 5/11 13:00 for 2 adults and 3 kids. Is there a table?
> **Human**: Yes, we have space.
> **AI**: Great! One of the kids needs a high chair/set. Also, is there parking available?
