## 1. NAS + tunnel infrastructure (prerequisite, out of repo)

- [ ] 1.1 Stand up an image store on the NAS (object dir or MinIO/WebDAV) with a write endpoint and a read path
- [ ] 1.2 Expose the read path publicly via a Cloudflare tunnel; note the stable public base URL
- [ ] 1.3 Protect the write endpoint (bearer token or Cloudflare Access service token); record the secret
- [ ] 1.4 Verify end-to-end by hand: PUT an image, GET it back over the public URL, confirm bytes match

## 2. Configuration surface

- [ ] 2.1 Add `NAS_MEDIA_UPLOAD_URL`, `NAS_MEDIA_PUBLIC_BASE`, `NAS_MEDIA_TOKEN` (optional), `NAS_MEDIA_MAX_BYTES` to `example.env`
- [ ] 2.2 Read the config in `app/_app.py` (or settings) so the values are available at startup
- [ ] 2.3 Document the NAS + Cloudflare-tunnel setup in `notes-ai/` and reference it from the README

## 3. NAS image host implementation

- [ ] 3.1 Create `app/exporters/hosts/nas.py` with `NasImageHost` implementing the `ImageHost` Protocol
- [ ] 3.2 Content-address objects: key = `sha256(data)` + extension derived from `mime`
- [ ] 3.3 Skip re-upload when the object already exists (HEAD check); always return `{public_base}/{key}`
- [ ] 3.4 Enforce size cap and short timeout; return `None` (log) on any failure — never raise
- [ ] 3.5 Export `NasImageHost` from `app/exporters/__init__.py`

## 4. Startup wiring

- [ ] 4.1 In `app/bot.py`, construct `NasImageHost(...)` and call `set_image_host(host)` when config is present
- [ ] 4.2 When config is absent/incomplete, skip registration (host stays `None`); log which state was chosen

## 5. Tests

- [ ] 5.1 Unit test: `upload()` returns the expected content-addressed URL for given bytes (transport mocked)
- [ ] 5.2 Unit test: identical bytes → identical URL; existing object → no re-transfer
- [ ] 5.3 Unit test: transport error / oversized input → `upload()` returns `None`, does not raise
- [ ] 5.4 Integration test (existing seam): with a fake host registered, Telegraph emits an `img` node; with none, a text mention

## 6. Verify live

- [ ] 6.1 Register the real host, publish a captured photo to Telegraph, confirm the image renders on the page
- [ ] 6.2 Kill the tunnel and confirm graceful degradation to a text mention (no publish failure)
- [ ] 6.3 `openspec validate nas-media-hosting --strict` passes; archive the change when complete
