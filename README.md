# formatter-bot

Forward it a pile of Telegram messages — text, photos, albums, files, voice — and it **captures**
the whole burst as one document you can **re-emit** in different formats. Built on
[botspot](https://github.com/calmmage/botspot); doubles as a showcase of botspot's media handling.

## How it works

1. **Capture** — forward/send a burst of messages (albums included). botspot's
   `message_aggregator` debounces them into one ordered document.
2. **Pick a format** — the bot replies with an inline keyboard.
3. **Get the artifact** — a file or a published link comes back.

### Formats

| Format | Media | Output |
|---|---|---|
| 📝 Markdown | reference | `.md` file (entities → bold/italic/links/code) |
| 🌐 HTML | **inline** (data URIs) | self-contained `.html` file |
| 📄 Plaintext | mention or drop | `.txt` file |
| 📰 Telegraph | **photos uploaded** | published telegra.ph link |

Roadmap: Notion, PDF, Obsidian-vault drop. See `notes-ai/`.

## Commands
- `/start`, `/help`
- `/format` — re-format the last captured batch
- `/settings` — default format, plaintext media policy, Telegraph token

## Architecture
One canonical `CapturedDoc` (ordered `Block`s of text + media); every format is a renderer over it.
`app/models.py` · `app/capture.py` · `app/renderers/` · `app/exporters/` · `app/formats.py` ·
`app/router.py`.

## Run
```bash
cp example.env .env   # set TELEGRAM_BOT_TOKEN; BOTSPOT_MESSAGE_AGGREGATOR_ENABLED=true is required
poetry install
poetry run python run.py
```

> **Note:** requires a botspot version that includes the `message_aggregator` component
> (`botspot/components/new/message_aggregator.py`). Ensure `botspot@main` is up to date.

## Tests
```bash
poetry run pytest
```
