---
name: pushover
description: Send push notifications through Pushover when the user asks for a notification or has authorized a notification when work finishes.
---

# Pushover

Send a notification using `scripts/send_pushover.py` relative to this skill's directory. Requires Python 3; uses only the standard library.

## Credentials

The script reads `PUSHOVER_API_TOKEN` (application token) and `PUSHOVER_USER_KEY` (recipient user or group key) from the environment, falling back to the same fields in `~/.config/pushover/credentials.json`. On Magnus's Mac, this private file is configured outside the repository, with directory permissions `700` and file permissions `600`. Environment variables take precedence per field.

Do not print or copy real keys into this repository, command arguments, chat, or logs. If credentials are missing, report the missing field names and ask the user to configure them privately. When checking setup, use mocked tests or credential validation; setup alone does not authorize a live notification.

Get an application token by registering an application at [Pushover](https://pushover.net/apps/build); the user key is available on the [dashboard](https://pushover.net/).

## Sending

Send only within the user's requested scope. A request such as “notify me through Pushover when this finishes” authorizes that completion notification; execute it when the condition is met without asking again. Merely using this skill for setup or testing does not authorize a live notification.

Use a short, factual message in the user's language. Include enough context to identify the work. The message limit is 1,024 characters and the optional title limit is 250 characters. If summarizing, preserve errors and required user actions.

Run from the skill directory, or substitute the actual absolute script path:

```bash
python3 scripts/send_pushover.py --title 'Codex' --message 'Arbetet är klart.'
```

For multiline text, a quoted heredoc avoids shell expansion:

```bash
python3 scripts/send_pushover.py --title 'Codex' <<'MESSAGE'
Verifieringen är klar.
Alla kontroller passerade.
MESSAGE
```

Optional flags:

- `--priority -2|-1|0|1`: defaults to `0`. Use `1` only when requested; it bypasses quiet hours. Emergency priority `2` is not supported.
- `--device NAME`: pass only if the user specifies a device. Without it, Pushover targets the recipient's active devices. Pushover may also broadcast to all devices when the named device is invalid.
- `--attachment /absolute/path/image.png`: attach one PNG or JPEG image, at most
  5,242,880 bytes (5 MiB). The script validates the size and image signature
  before sending, then uses Pushover's Base64 attachment fields. A text message
  is still required. Never print attachment Base64 or credentials.

When the user asks to send an image, inspect it and verify the intended file
and recipient before running the sender. The user's send request authorizes
that image notification; do not send extra test notifications. For example:

```bash
python3 scripts/send_pushover.py --title 'ATP-betting' --attachment /absolute/path/poster.png <<'MESSAGE'
Status för de tre bokförda pappersspelen. Se affischen.
MESSAGE
```

Exit code `0` means Pushover accepted the request, not that the user read it. Other exit codes indicate an error or an unknown outcome. The script makes one request with no automatic retries. After a timeout, connection failure, or malformed response, report uncertainty; do not resend automatically because the first request may have been accepted.

API reference: [Pushover Message API](https://pushover.net/api).

## Local verification

Run `python3 -m unittest discover -s tests -v`. Tests mock the HTTP call and never send a notification.
