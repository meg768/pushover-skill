#!/usr/bin/env python3
"""Send one Pushover notification using private local credentials or environment variables."""

import argparse
import base64
from http.client import HTTPException
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ENDPOINT = "https://api.pushover.net/1/messages.json"
CREDENTIALS_FILE = Path.home() / ".config" / "pushover" / "credentials.json"
MAX_ATTACHMENT_BYTES = 5_242_880


def attachment_fields(path):
    """Read one PNG/JPEG attachment without requiring an imaging dependency."""
    try:
        with path.open('rb') as image:
            data = image.read(MAX_ATTACHMENT_BYTES + 1)
    except OSError:
        raise ValueError('Could not read image attachment.') from None
    if not data or len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError('Image attachment must contain 1–5,242,880 bytes (5 MiB).')
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        content_type = 'image/png'
    elif data.startswith(b'\xff\xd8\xff'):
        content_type = 'image/jpeg'
    else:
        raise ValueError('Image attachment must be PNG or JPEG.')
    return {
        'attachment_base64': base64.b64encode(data).decode('ascii'),
        'attachment_type': content_type,
    }


def load_credentials():
    names = ("PUSHOVER_API_TOKEN", "PUSHOVER_USER_KEY")
    credentials = {name: os.environ.get(name, "").strip() for name in names}
    if all(credentials.values()):
        return credentials
    try:
        local = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        local = {}
    except (OSError, ValueError, UnicodeError):
        raise ValueError("Could not read private Pushover credentials file.") from None
    if not isinstance(local, dict) or any(
        not isinstance(local.get(name, ""), str) for name in names
    ):
        raise ValueError("Invalid private Pushover credentials format.")
    return {name: credentials[name] or local.get(name, "").strip() for name in names}


def api_errors(body):
    """Return only the API's error messages, never its full response."""
    try:
        result = json.loads(body)
    except (ValueError, UnicodeError):
        return "No valid error details returned."
    errors = result.get("errors") if isinstance(result, dict) else None
    if isinstance(errors, list) and all(isinstance(item, str) for item in errors):
        return "; ".join(errors) or "No error details returned."
    return "No error details returned."


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", help="Message text; otherwise read from stdin")
    parser.add_argument("--title", help="Title; defaults to the Pushover app name")
    parser.add_argument("--device", help="Optional Pushover device name")
    parser.add_argument("--priority", type=int, choices=(-2, -1, 0, 1), default=0)
    parser.add_argument("--attachment", type=Path, help="Optional PNG/JPEG image, up to 5 MiB")
    args = parser.parse_args(argv)

    message = args.message
    if message is None:
        if sys.stdin.isatty():
            parser.error("provide --message or pipe a message to stdin")
        message = sys.stdin.read()
    if not message.strip() or len(message) > 1024:
        parser.error("message must contain 1–1024 characters and not be blank")
    if args.title is not None and len(args.title) > 250:
        parser.error("title must not exceed 250 characters")

    try:
        attachment = attachment_fields(args.attachment) if args.attachment else {}
        credentials = load_credentials()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    missing = [name for name, value in credentials.items() if not value]
    if missing:
        print("Missing credentials: " + ", ".join(missing), file=sys.stderr)
        return 1

    payload = {
        "token": credentials["PUSHOVER_API_TOKEN"],
        "user": credentials["PUSHOVER_USER_KEY"],
        "message": message,
        "priority": args.priority,
        **attachment,
    }
    for name in ("title", "device"):
        value = getattr(args, name)
        if value:
            payload[name] = value

    request = Request(ENDPOINT, data=urlencode(payload).encode("utf-8"), method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            result = json.load(response)
        if not isinstance(result, dict) or "status" not in result:
            raise ValueError("Unexpected response format")
        if result.get("status") != 1:
            detail = api_errors(json.dumps(result))
            for secret in credentials.values():
                detail = detail.replace(secret, "[redacted]")
            print("Pushover rejected the request: " + detail, file=sys.stderr)
            return 1
    except HTTPError as error:
        try:
            detail = api_errors(error.read())
        except (HTTPException, OSError, ValueError):
            detail = "Could not read error details."
        finally:
            error.close()
        for secret in credentials.values():
            detail = detail.replace(secret, "[redacted]")
        print(f"Pushover HTTP {error.code}: {detail}", file=sys.stderr)
        return 1
    except (HTTPException, URLError, OSError, ValueError) as error:
        print(
            f"Pushover outcome unknown ({type(error).__name__}); no automatic retry.",
            file=sys.stderr,
        )
        return 1

    print("Pushover accepted the notification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
