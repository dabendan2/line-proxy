# Restaurant Reservation State Machine (LINE Agent)

This pattern enables a LINE Proxy to handle restaurant bookings by transitioning through specific states.

## State Definitions

| State | Prompt to User | Expected Input | Next State |
| :--- | :--- | :--- | :--- |
| `IDLE` | (Triggered by "訂餐廳") | Restaurant Name | `ASK_PEOPLE` |
| `ASK_PEOPLE` | "好的，請問幾位用餐？" | Number (e.g., "4位") | `ASK_TIME` |
| `ASK_TIME` | "明白。預計什麼時候呢？(如 18:30)" | Time / Date | `ASK_PHONE` |
| `ASK_PHONE` | "最後請提供您的聯絡電話，我這就幫您處理。" | Phone Number | `PROCESSING` |
| `PROCESSING` | "正在為您連線預約系統，請稍候..." | (N/A) | `CONFIRMED` / `FAILED` |

## Example Implementation Snippet (Python)

```python
def handle_reservation(state, incoming_text):
    text = incoming_text.strip()
    
    if state['sub_state'] == "ASK_PEOPLE":
        state['booking_data']['people'] = text
        state['sub_state'] = "ASK_TIME"
        return "好的，請問幾位用餐？"
        
    elif state['sub_state'] == "ASK_TIME":
        state['booking_data']['time'] = text
        state['sub_state'] = "ASK_PHONE"
        return f"明白，{text}。最後請提供您的聯絡電話，我這就幫您處理。"
        
    # ... and so on
```

## Integration with Web Scraping
Once the state reaches `PROCESSING`, the script should:
1. Open a new tab in the same browser context.
2. Navigate to the restaurant's booking site (e.g., inline.app, opentable).
3. Use `page.fill()` and `page.click()` to complete the form using data from `state['booking_data']`.
4. Capture a screenshot of the confirmation page.
5. Send the confirmation details (and screenshot) back to the LINE chat.
