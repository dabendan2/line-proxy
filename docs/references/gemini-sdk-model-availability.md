# Gemini SDK Model Availability Quirks

In the `google.genai` SDK environment, some common model names may return `404 NOT_FOUND` depending on the API version or account permissions.

## Observed Behavior
- `gemini-2.0-flash-exp`: Often fails with 404.
- `gemini-1.5-flash`: Often fails with 404.
- `gemini-3-flash-preview`: Highly stable and available.
- `gemini-flash-latest`: Generally available.

## Troubleshooting
If a model fails, run this snippet to check available names:
```python
for m in client.models.list():
    print(m.name)
```