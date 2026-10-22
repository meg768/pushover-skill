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

## Test

```bash
python3 scripts/send.py --title "Codex" --message "Hello from Codex"
```

From Codex, ask: **"Send me a Pushover notification when the tests finish."**

The skill does not create background jobs or automatically monitor tasks. Codex must invoke the script after the relevant work completes.

## Options

```bash
python3 scripts/send.py --title "Build" --message "All tests passed" --priority 0
```

Supports priorities -2 through 1 and optional `--sound`. Emergency priority 2 requires additional Pushover parameters and is intentionally not supported.
