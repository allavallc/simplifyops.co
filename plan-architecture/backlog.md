# Backlog

## Pending

### Failed-needs-review approval surface (Story: gateway-review-001)

Work items that exhaust 3 retries move to `failed_needs_review` and are currently only logged.

Build an admin view in people-whitelist and a Telegram approval flow so the operator can:
- See `failed_needs_review` items (message, sender, error, attempt count)
- Choose: retry the item (reset to `ready`) or discard it (`completed` with a note)
- Optionally configure: receive a Telegram notification when an item hits this state vs. check the admin UI manually

**DB surface already exists:** `work_items.status = 'failed_needs_review'`, `work_items.error_summary`.
**Gateway hook needed:** after `_set_status(failed_needs_review)`, optionally call a configurable notifier.
