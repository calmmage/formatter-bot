---
type: project-vision
project: formatter-bot
date: 2026-06-26
---

# formatter-bot — vision & architecture

## What it is
Forward a pile of messages to the bot (text, photos, albums, files, voice). It **captures** the
whole burst as one document and lets you **re-emit** it in a chosen format. Doubles as a showcase
of botspot's media-handling.

Origin: this replaces the dead `forwarder-bot` (legacy `bot_lib` stack, broken by calmlib v2 — see
the coolify-migration tracker, TASK C). Rather than resurrect the dead stack we rebuilt the idea
fresh on the maintained **botspot** stack, into the pre-existing `calmmage/formatter-bot` scaffold.

## Core architecture: one canonical capture → many renderers
Every forwarded burst becomes a `CapturedDoc` — an ordered list of `Block`s (one per message),
each holding the message's HTML text (entities preserved) + media (as Telegram file_ids, fetched
lazily at render time). Every output is just a renderer/exporter over this one structure.

```
forward burst ─▶ MessageAggregator.collect (botspot) ─▶ capture_batch ─▶ CapturedDoc
                                                                              │
        ┌──────────────┬──────────────┬───────────────┬─────────────────────┤
     plaintext       markdown        html (media)    telegraph           (future: notion,
     (strip)         (entities)      data-URIs       upload+publish        pdf, obsidian-drop)
```

Add a format = add one entry to `app/formats.py`. Nothing else changes.

## Layout
- `app/models.py` — `CapturedDoc`, `Block`, `MediaItem`/`MediaKind`.
- `app/capture.py` — messages → CapturedDoc (uses botspot `get_message_attachments`).
- `app/renderers/` — `markdown`, `html` (inlines media as base64 data URIs), `plaintext`,
  `media` (lazy download via botspot `download_telegram_file`), `util` (html→md/text).
- `app/exporters/telegraph.py` — publish to telegra.ph (anonymous or per-user token).
- `app/formats.py` — `{key: (label, producer)}` registry.
- `app/store.py` — in-memory last-doc + per-user prefs (MVP).
- `app/router.py` — catch-all capture handler + inline format keyboard + callbacks.
- `app/routers/settings.py` — `/settings`: default format, plaintext media policy, telegraph token.

## Botspot feature added (the "multi-message plugin")
`botspot/components/new/message_aggregator.py` — finished the previously-broken `multi_forward_handler`
draft into a real component: `get_message_aggregator().collect(message)` debounces a burst (default
1s window, album-aware) and returns the full ordered batch to the first settling call (None to the
rest). Wired into settings/bot_manager/dependency_manager/deps_getters/`__init__`; tested in
`tests/components/new/test_message_aggregator.py`. Also promoted `get_message_attachments`,
`download_telegram_file`, `get_attachment_format` to the public `botspot.utils` surface.

## Format tiers (roadmap)
- **Done (MVP):** capture+media · Markdown · HTML (media inline) · Plaintext (media mention/drop) · Telegraph.
- **Next:** Notion (per-user token → blocks), PDF (HTML→PDF via weasyprint), Obsidian-vault drop.
- **Parked:** Substack (no clean publish API), email, zip bundle, raw JSON.

## Decisions captured
- Batch sealing: album + 1s time-window auto-seal; `/format` re-emits the last batch. (`/done` not
  needed given the debounce; can add later.)
- Plaintext media default = **mention** (`[📷 photo]`), toggle to drop. Never silently lose media.
- HTML & Telegraph are the media-carrying formats (Petr: "I want some media supporting format").

## Open follow-ups
- **Blocking deploy:** botspot changes are local/unpushed — formatter-bot pulls `botspot@main`, so
  botspot must be committed+pushed before the bot can build/run anywhere but locally.
- Persist `CapturedDoc` to mongo (survive restarts; file_ids are reasonably long-lived).
- Telegraph photo upload via `telegra.ph/upload` is semi-official and may rate-limit → falls back to
  text mention; revisit if it proves flaky.
- Rename/Coolify: create `formatter-bot` app on NEW (ARM) at deploy time; retire old forwarder app.
- Live E2E with a real bot token (telegram-bot-tester) — deferred to deploy.
