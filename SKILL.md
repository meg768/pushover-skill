---
name: pushover
description: Send push notifications through Pushover when the user asks to be notified about builds, tests, tasks, or other results.
---

# Pushover

Use this skill when the user asks to send a Pushover notification, including notifications after a command, build, or test completes.

## Send a notification

Run the bundled script:

```bash
python3 scripts/send.py --title "Codex" --message "Build finished"
```

Credentials must be supplied through environment variables `PUSHOVER_USER_KEY` and `PUSHOVER_API_TOKEN`. Never request that credentials be committed, printed, or embedded in source code.

Options:
- `--title`: notification title (optional, defaults to Codex).
- `--message`: required notification text.
- `--priority`: optional Pushover priority from -2 through 1 (defaults to 0). Emergency priority 2 is deliberately unsupported.
- `--sound`: optional Pushover sound name.

When the user requests notification after work completes, execute the task first, then send a notification containing the actual result. If a task fails, report the failure accurately. Do not claim a notification was delivered unless the API confirms acceptance. Pushover acceptance does not prove the device displayed the notification.

Do not send notifications unless the user requested one, or explicitly configured a workflow to send them.
