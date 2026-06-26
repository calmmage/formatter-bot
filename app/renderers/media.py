"""Pull captured media bytes back out of Telegram via botspot's downloader."""

from types import SimpleNamespace
from typing import Optional

from botspot.utils import download_telegram_file

from app.models import MediaItem, MediaKind

_DEFAULT_MIME = {
    MediaKind.photo: "image/jpeg",
    MediaKind.video: "video/mp4",
    MediaKind.video_note: "video/mp4",
    MediaKind.audio: "audio/mpeg",
    MediaKind.voice: "audio/ogg",
    MediaKind.document: "application/octet-stream",
}


def mime_for(item: MediaItem) -> str:
    return item.mime_type or _DEFAULT_MIME.get(item.kind, "application/octet-stream")


async def fetch_bytes(item: MediaItem) -> Optional[bytes]:
    """Download a media item's bytes. Returns None if the file can't be fetched."""
    try:
        # botspot's downloader only needs an object exposing `.file_id` for the aiogram path
        binio = await download_telegram_file(SimpleNamespace(file_id=item.file_id))
        binio.seek(0)
        return binio.read()
    except Exception:
        return None
