## Why

Telegraph (and any future URL-embedding exporter) can only show images that live at a public
URL. `telegra.ph/upload` — the endpoint we relied on — is discontinued and now returns `400
"Unknown error"` for every image, so captured photos silently degrade to `[📷 photo]` text
mentions. The renderer already delegates to a pluggable `ImageHost` seam (`app/exporters/imagehost.py`),
but no host is registered, so the seam is a no-op. We want a **self-hosted** image host on the
home NAS, exposed over a Cloudflare tunnel — privacy-preserving (nothing leaves to a third party,
no bot-token exposure) and giving Telegraph a stable public URL to embed.

## What Changes

- Add a **NAS-backed `ImageHost`** implementation that uploads image bytes to the home NAS and
  returns a public URL served via a Cloudflare tunnel.
- **Register** the host at bot startup when configured (env-gated); when unconfigured, behavior is
  unchanged (text mentions) — no regression.
- Content-address uploaded images (hash-named) so re-publishing the same photo is idempotent and
  cheap; set long/immutable cache headers.
- Add configuration (env) for the NAS endpoint, public base URL, and an auth token; document the
  NAS + Cloudflare-tunnel setup.
- Telegraph publish path unchanged in shape — it already calls `get_image_host()`; only a real host
  now exists.

## Capabilities

### New Capabilities
- `media-hosting`: upload captured media (initially photos) to a self-hosted store and return a
  stable public URL for embedding in published outputs (Telegraph first). Covers the host
  interface contract, the NAS/Cloudflare-tunnel backend, addressing/caching, configuration, and
  graceful degradation when unavailable.

### Modified Capabilities
<!-- No existing OpenSpec specs yet (freshly initialized); nothing to modify. -->

## Impact

- **Code:** new `app/exporters/hosts/nas.py` (host impl); startup wiring in `app/bot.py` to call
  `set_image_host(...)`; config surface in `app/_app.py` / env. `app/exporters/telegraph.py` and
  `app/exporters/imagehost.py` unchanged (the seam already exists).
- **Config/secrets:** new env vars (`NAS_MEDIA_*` / Cloudflare hostname + token). No secrets in
  the repo.
- **Infra (out of repo):** an upload receiver on the NAS + a Cloudflare tunnel exposing its public
  read URL. This is the load-bearing prerequisite and is tracked in tasks.
- **Deps:** none beyond `httpx` (already present).
- **Privacy:** media leaves the process only to infrastructure the user controls; no third-party
  host, no bot token in public URLs. Aligns with the redact-before-egress posture.
