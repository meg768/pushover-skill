# Pushover skill for Codex

A minimal, reusable Codex skill for sending push notifications through [Pushover](https://pushover.net/). Uses Python 3's standard library only.

## Install globally

Clone this repository, then symlink the skill into your global Codex skills directory:

```bash
git clone https://github.com/meg768/pushover-skill.git
mkdir -p ~/.agents/skills
ln -s "$(pwd)/pushover-skill" ~/.agents/skills/pushover
```

Run the commands from the directory where you want the clone to live. If `~/.agents/skills/pushover` already exists, inspect it before replacing it. Restart Codex if necessary to discover the skill.

## Configure

Create an application/API token at [Pushover](https://pushover.net/apps/build). Find your user key on your Pushover dashboard.

Set these variables in the environment that **launches Codex**:

```bash
export PUSHOVER_USER_KEY="your-user-key"
export PUSHOVER_API_TOKEN="your-app-token"
```

Do not commit real credentials or put them in `SKILL.md`. Environment variables set in a terminal are not necessarily inherited by a Codex desktop app launched from Finder.

Alternatively, store the same fields in `~/.config/pushover/credentials.json`, outside the repository. Use directory permissions `700` and file permissions `600`. Environment variables take precedence per field.

## Local verification

```bash
python3 -m unittest discover -s tests -v
```

Tests mock the HTTP call and do not send notifications.

From Codex, ask: **"Send me a Pushover notification when the tests finish."**

The skill does not create background jobs or automatically monitor tasks. Codex must invoke the script after the relevant work completes.

## Options

```bash
python3 scripts/send_pushover.py --title "Build" --message "All tests passed" --priority 0
```

Supports priorities -2 through 1, optional `--device`, and one PNG/JPEG image via `--attachment` (up to 5 MiB). Message text can also be read from stdin. Emergency priority 2 is intentionally not supported. See `SKILL.md` for usage and handling uncertain outcomes.

The original `scripts/send.py` is retained for existing callers; it uses environment credentials and supports `--sound`.
