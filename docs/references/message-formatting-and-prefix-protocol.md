# LINE Proxy Message Formatting and Prefix Protocol

## The "Double Prefix" Issue
During the "Hangman" session, messages were appearing as `[Hermes] [Hermes] ...`. This was caused by the model (Gemini) being too helpful and adding the prefix itself, combined with the underlying `line_utils.py` send function which also prepends `[Hermes]`.

### Core Resolution
1. **Prompt Instruction**: The system prompt (in `engine.py`) and the `etiquette.md` file must explicitly forbid the model from generating any identity tags like `[Hermes]`.
2. **Code Sanitization**: The `engine.py` logic was patched to strip any leading `[Hermes]` from the model's output before passing it to `line_utils.send_message`.
3. **Identity Verification**: The model should still "act" as Hermes and provide the introduction `您好，我是 俊羽 的AI代理 Hermes。` but without the square-bracket tag.

## Environment Efficiency
- **Avoid manual exports**: The proxy environment is set up to load `.env` automatically.
- **Lock File Sanitization**: `dabendan.test` -> `dabendan_test.pid`. This is crucial for manual troubleshooting and cleanup of hung processes.

## Model Reliability
- **404 NOT_FOUND**: `gemini-2.0-flash-exp` and `gemini-1.5-flash` often fail with 404 in this SDK environment.
- **Recommended Model**: Always default to `gemini-3-flash-preview` or `gemini-flash-latest` for LINE automation to ensure stability and lower latency.
