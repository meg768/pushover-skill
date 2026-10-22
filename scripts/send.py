#!/usr/bin/env python3
"""Send a Pushover notification using only Python's standard library."""

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.pushover.net/1/messages.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a Pushover notification")
    parser.add_argument("--message", required=True, help="Notification body")
    parser.add_argument("--title", default="Codex", help="Notification title")
    parser.add_argument("--priority", type=int, choices=range(-2, 2), default=0)
    parser.add_argument("--sound", help="Optional Pushover sound name")
    args = parser.parse_args()

    user = os.environ.get("PUSHOVER_USER_KEY")
    token = os.environ.get("PUSHOVER_API_TOKEN")
    if not user or not token:
        print("Missing PUSHOVER_USER_KEY or PUSHOVER_API_TOKEN environment variable.", file=sys.stderr)
        return 2

    data = {
        "user": user,
        "token": token,
        "title": args.title,
        "message": args.message,
        "priority": args.priority,
    }
    if args.sound:
        data["sound"] = args.sound

    request = Request(
        API_URL,
        data=urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except HTTPError as exc:
        print(f"Pushover HTTP error: {exc.code}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, ValueError) as exc:
        print(f"Pushover request failed: {exc}", file=sys.stderr)
        return 1

    if payload.get("status") != 1:
        print("Pushover rejected the notification: " + ", ".join(payload.get("errors", [])), file=sys.stderr)
        return 1

    print("Pushover accepted the notification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
