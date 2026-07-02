"""Pluggable image host for publish targets that embed images by URL (e.g. Telegraph).

telegra.ph/upload was discontinued (every upload 400s), so hosting must happen elsewhere. This
defines the seam: a host takes image bytes and returns a public URL. The default host is None
(no hosting -> images degrade to text mentions). A NAS-backed host published over a Cloudflare
tunnel is the planned drop-in — see notes-ai/2026-06-26-formatter-bot-vision.md.
"""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class ImageHost(Protocol):
    async def upload(self, data: bytes, *, filename: str, mime: str) -> Optional[str]:
        """Return a public URL for the image bytes, or None if hosting failed."""
        ...


_host: Optional[ImageHost] = None


def set_image_host(host: Optional[ImageHost]) -> None:
    """Register the process-wide image host (called at startup once configured)."""
    global _host
    _host = host


def get_image_host() -> Optional[ImageHost]:
    return _host
