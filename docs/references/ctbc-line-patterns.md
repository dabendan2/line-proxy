# CTBC (中國信託) LINE Notification Patterns

The CTBC official account uses complex Flex Messages for transaction notifications.

## Common Data Attributes

When inspecting the DOM for CTBC messages, look for these specific attributes on the message container:

- `data-message-content`: Contains the preview text, e.g., `"🔔即時入帳通知🔔"` or `"繳款提醒通知"`.
- `data-message-content-prefix`: Usually contains the timestamp and account name, e.g., `"10:15 中國信託 "`.
- `data-timestamp`: Unix timestamp in milliseconds.

## Transaction Content (Inside Shadow DOM)

Once you extract text from the `flex-renderer` Shadow DOM, expect these patterns:

### Deposit Notification (入帳)
- `新臺幣[金額]元`
- `入帳時間：[YYYY/MM/DD HH:MM:SS]`
- `入帳帳號後四碼：[XXXX]`

### Payment Reminder (繳款提醒)
- `[房貸自動扣繳提醒通知]`
- `本行將於[MM/DD]自扣本期應繳金額`

## Troubleshooting Missing Records
If a record (like 4/24) is missing:
1. Check the earliest `data-timestamp` in the chat history.
2. If the earliest timestamp is after the requested date (e.g., Apr 29), the extension has reached its **Sync Depth Limit**. 
3. User must provide a screenshot or use mobile to view older history.
