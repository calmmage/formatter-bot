"""Turn a batch of Telegram messages into a CapturedDoc.

Uses botspot's media helpers so the media handling stays in the framework (this bot doubles as
a botspot media-handling showcase).
"""

from datetime import datetime, timezone
from typing import List, Optional

from aiogram.types import Audio, Document, Message, PhotoSize, Video, VideoNote, Voice
from botspot.utils import get_message_attachments

from app.models import Block, CapturedDoc, MediaItem, MediaKind


def _media_kind(att) -> Optional[MediaKind]:
    if isinstance(att, PhotoSize):
        return MediaKind.photo
    if isinstance(att, Video):
        return MediaKind.video
    if isinstance(att, VideoNote):
        return MediaKind.video_note
    if isinstance(att, Audio):
        return MediaKind.audio
    if isinstance(att, Voice):
        return MediaKind.voice
    if isinstance(att, Document):
        return MediaKind.document
    return None


def _media_item(att) -> Optional[MediaItem]:
    kind = _media_kind(att)
    if kind is None:
        return None
    return MediaItem(
        kind=kind,
        file_id=att.file_id,
        file_name=getattr(att, "file_name", None),
        mime_type=getattr(att, "mime_type", None),
    )


def _html_text(message: Message) -> Optional[str]:
    """HTML rendering of the message text/caption with entities preserved."""
    if message.text is None and message.caption is None:
        return None
    try:
        return message.html_text
    except Exception:
        return message.text or message.caption


def _sender_name(message: Message) -> Optional[str]:
    """Best-effort original author for forwarded messages, else the sender."""
    origin = getattr(message, "forward_origin", None)
    if origin is not None:
        for attr in ("sender_user", "sender_chat", "chat"):
            ent = getattr(origin, attr, None)
            if ent is not None:
                return getattr(ent, "full_name", None) or getattr(ent, "title", None)
        name = getattr(origin, "sender_user_name", None)
        if name:
            return name
    if message.from_user:
        return message.from_user.full_name
    return None


def capture_batch(messages: List[Message]) -> CapturedDoc:
    blocks: List[Block] = []
    for m in messages:
        media = [item for att in get_message_attachments(m) if (item := _media_item(att))]
        blocks.append(
            Block(
                message_id=m.message_id,
                ts=m.date,
                sender=_sender_name(m),
                text_html=_html_text(m),
                text_plain=(m.text or m.caption),
                media=media,
            )
        )
    user_id = messages[0].from_user.id if messages[0].from_user else messages[0].chat.id
    return CapturedDoc(user_id=user_id, created_at=datetime.now(timezone.utc), blocks=blocks)
