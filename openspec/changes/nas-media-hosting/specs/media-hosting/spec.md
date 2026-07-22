## ADDED Requirements

### Requirement: Self-hosted image host registration

The system SHALL register a NAS-backed image host at startup when — and only when — the required
configuration is present. When configuration is absent, the system SHALL leave the image host
unset so that URL-embedding exporters degrade to text mentions with no error.

#### Scenario: Host configured
- **WHEN** the bot starts and the NAS upload URL and public base URL are configured
- **THEN** a NAS image host is registered via `set_image_host(...)`
- **AND** `get_image_host()` returns that host

#### Scenario: Host not configured
- **WHEN** the bot starts and the NAS configuration is absent or incomplete
- **THEN** no image host is registered
- **AND** `get_image_host()` returns `None`
- **AND** startup completes normally

### Requirement: Upload returns a public URL

The image host SHALL accept image bytes and return a publicly reachable URL that serves those exact
bytes over the Cloudflare tunnel. The host SHALL address objects by the SHA-256 hash of their
content so that uploading identical bytes yields the same URL.

#### Scenario: Successful upload
- **WHEN** `upload(data, filename=..., mime="image/jpeg")` is called with valid image bytes
- **THEN** the bytes are stored on the NAS under a content-addressed key
- **AND** the method returns `{public_base}/{sha256}.jpg`
- **AND** an HTTP GET of that URL returns the same bytes

#### Scenario: Idempotent re-upload
- **WHEN** `upload(...)` is called twice with identical bytes
- **THEN** both calls return the same URL
- **AND** the second call does not re-transfer the bytes if the object already exists

### Requirement: Graceful failure

The image host SHALL return `None` (never raise) when it cannot produce a public URL — including
upload timeout, transport error, missing credentials, or oversized input — so that publishing
continues and the media degrades to a text mention.

#### Scenario: NAS unreachable
- **WHEN** `upload(...)` is called and the NAS/tunnel is unreachable or times out
- **THEN** the method returns `None`
- **AND** the failure is logged
- **AND** the Telegraph publish still succeeds with the image shown as a text mention

#### Scenario: Oversized image
- **WHEN** `upload(...)` is called with bytes larger than the configured maximum
- **THEN** the method returns `None` without attempting the upload

### Requirement: Telegraph embeds hosted images

When an image host is registered, the Telegraph exporter SHALL embed each photo as an `img` node
pointing at the host's returned URL; when hosting fails or no host is registered, it SHALL emit the
existing `[<media label>]` text mention.

#### Scenario: Photo hosted successfully
- **WHEN** a captured doc with a photo is published to Telegraph and the host returns a URL
- **THEN** the published page contains an `img` element whose `src` is the returned URL

#### Scenario: Photo hosting unavailable
- **WHEN** a captured doc with a photo is published to Telegraph and no host is registered (or it returns `None`)
- **THEN** the published page shows the photo as a `[📷 photo]` text mention
