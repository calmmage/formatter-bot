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

## 2026-07-02 update — post format, AI titles, Telegraph reality-check
Petr feedback round: (1) add a **post** format, (2) **LLM-generated title** with style-picker
buttons, (3) fix Telegraph media.

- **`post` format** (`app/post.py`) — re-emits the doc as a single Telegram post: media resent by
  file_id into album(s), combined text as caption/message. Overflow resolved interactively:
  >10 media → *"First 10" / "All (split albums)"*; text over ~1000 (with media) / ~4000 (plain) →
  *"Attach as file" / "Split messages" / "Trim"*. Now the primary media-carrying output. Telegram
  album rules handled: photos/videos grouped, documents/audio in their own runs, voice/video_note
  sent singly (`_runs`).
- **AI titles** (`app/titler.py`) — `🏷 Title (AI)` button → style picker (Concise / Descriptive /
  Catchy / Emoji) → `botspot.aquery_llm_text` (model `claude-4.5-haiku`). Stored on
  `CapturedDoc.title_override`; `display_title` feeds post header, Telegraph title, file captions.
  Needs `BOTSPOT_LLM_PROVIDER_ENABLED=true` + `ANTHROPIC_API_KEY` (wired in `bot.py`).
- **Telegraph media** — root-caused: **`telegra.ph/upload` is discontinued** (400 "Unknown error"
  for every image, any headers — verified). Reworked into a **pluggable `ImageHost` seam**
  (`app/exporters/imagehost.py`): telegraph embeds photos by URL from the registered host; default
  host = None → photos degrade to `[📷 photo]` text mentions (no token leak, no third-party egress).

### Telegraph image host — chosen direction (Petr)
Host images on the **home NAS**, publish over a **Cloudflare tunnel** → Telegraph embeds that public
URL. Privacy-preserving (self-hosted, no bot-token exposure, nothing to a third party). Drop-in:
implement `ImageHost.upload()` against the NAS endpoint + `set_image_host(...)` at startup — the
telegraph renderer needs no change. **Not built yet** (own infra task).

## Open follow-ups
- **Telegraph NAS image host** — NAS media hosting + Cloudflare tunnel, implement + register the
  `ImageHost`. Until then Telegraph media = text mentions.
- Persist `CapturedDoc` to mongo (survive restarts; file_ids are reasonably long-lived).
- Rename Coolify app `forwarder-bot` → `formatter-bot` (Petr: "rename later").
- Live E2E — the bot is live at @calmmage_Forwarder_bot; forward a burst with a photo album + long
  text to exercise post overflow + AI title.
