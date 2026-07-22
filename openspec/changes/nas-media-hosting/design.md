## Context

The Telegraph exporter (`app/exporters/telegraph.py`) builds a page of nodes and, for each photo,
calls `_host_image(item)` → `get_image_host().upload(...)`. The `ImageHost` Protocol and the
process-wide `set_image_host` / `get_image_host` registry already exist
(`app/exporters/imagehost.py`). No concrete host is registered, so `get_image_host()` returns
`None` and photos fall back to text mentions. Media bytes are fetched on demand from Telegram by
`app/renderers/media.py::fetch_bytes(item)` (resolves file_id → bytes).

The user has a home NAS and Cloudflare tunnels available. The goal is to fill the seam with a
NAS-backed host so Telegraph pages render real images, without leaking content to third parties or
exposing the bot token.

## Goals / Non-Goals

**Goals:**
- Register a concrete `ImageHost` that returns a stable, publicly-reachable URL for a photo.
- Self-hosted only: bytes go to the user's NAS; the public URL is served via Cloudflare tunnel.
- Zero regression when unconfigured — absent config, the host is not registered and behavior is
  identical to today (text mentions).
- Idempotent, cache-friendly uploads (content-addressed) so re-publishing is cheap.

**Non-Goals:**
- Hosting non-image media (video/audio/documents) — Telegraph can't embed those anyway; photos
  first. The interface stays generic so this can extend later.
- Building the NAS receiver or Cloudflare tunnel *in this repo* — those are infra steps (tracked in
  tasks), consumed here via config.
- A general CDN, deletion/GC lifecycle, or auth for the public read path (images are
  unguessable-by-hash but world-readable, matching Telegraph's own model).

## Decisions

- **Interface unchanged.** Implement the existing `ImageHost` Protocol:
  `async def upload(data, *, filename, mime) -> Optional[str]`. Return `None` on any failure so the
  renderer degrades gracefully (never raises into publish).
- **Content addressing.** Object key = `sha256(data)` + extension from `mime`. Same image → same
  URL; upload can be skipped if a HEAD says it already exists. Public URL =
  `{public_base}/{key}`.
- **Transport = HTTP PUT to the NAS over the tunnel** (simplest portable option): the bot uploads
  to a write endpoint (tunnel-auth via bearer token / Cloudflare Access service token), reads back
  via the public `{public_base}`. Alternative backends (S3-compatible MinIO on the NAS, WebDAV) are
  possible behind the same `ImageHost` — PUT chosen for least moving parts.
- **Config via env**, surfaced on `App`/settings: `NAS_MEDIA_UPLOAD_URL`, `NAS_MEDIA_PUBLIC_BASE`,
  `NAS_MEDIA_TOKEN` (optional). Startup wiring in `app/bot.py`: if the required vars are present,
  construct `NasImageHost(...)` and call `set_image_host(host)`; else skip.
- **Timeouts + size guard.** Cap upload size (e.g. skip > N MB) and use a short timeout; failure →
  `None` → text mention. Telegraph itself only needs modest images.

## Risks / Trade-offs

- **Availability coupling:** if the NAS or tunnel is down, Telegraph photos silently degrade to
  mentions. Acceptable (matches current behavior) and logged.
- **Public readability:** anyone with the hashed URL can view the image (same trust model as
  Telegraph's own image hosting). Hash-naming makes URLs unguessable but not access-controlled;
  documented as a known trade-off. Do not host sensitive captures via Telegraph.
- **Infra dependency outside the repo:** the NAS receiver + tunnel are prerequisites; the change is
  not "done" until they exist and a real publish renders an image. Tracked explicitly in tasks.
- **file_id → bytes cost:** each publish re-downloads photos from Telegram; fine at MVP volume,
  revisit with caching if it becomes hot.
