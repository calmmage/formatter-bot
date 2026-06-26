"""Canonical capture model.

A forwarded burst becomes a `CapturedDoc` — an ordered list of `Block`s (one per message),
each holding the message's formatted text (HTML, entities preserved) and any media. Every
output format is just a renderer over this one structure.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MediaKind(str, Enum):
    photo = "photo"
    document = "document"
    video = "video"
    audio = "audio"
    voice = "voice"
    video_note = "video_note"


class MediaItem(BaseModel):
    kind: MediaKind
    file_id: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None


class Block(BaseModel):
    """One captured message."""

    message_id: int
    ts: datetime
    sender: Optional[str] = None
    text_html: Optional[str] = None  # entities preserved (aiogram html_text)
    text_plain: Optional[str] = None
    media: List[MediaItem] = Field(default_factory=list)

    @property
    def has_text(self) -> bool:
        return bool(self.text_plain and self.text_plain.strip())


class CapturedDoc(BaseModel):
    user_id: int
    created_at: datetime
    blocks: List[Block] = Field(default_factory=list)

    @property
    def n_media(self) -> int:
        return sum(len(b.media) for b in self.blocks)

    @property
    def title(self) -> str:
        """Derive a short title from the first non-empty line of text."""
        for b in self.blocks:
            if b.text_plain and b.text_plain.strip():
                first = b.text_plain.strip().splitlines()[0]
                return first[:80]
        if self.n_media:
            return f"{self.n_media} media item(s)"
        return "Captured messages"
