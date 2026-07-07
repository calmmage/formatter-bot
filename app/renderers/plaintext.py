"""Plaintext renderer — formatting stripped, media mentioned (or dropped)."""

from app.models import CapturedDoc
from app.renderers.util import media_label


def render_plaintext(doc: CapturedDoc, drop_media: bool = False) -> str:
    groups: list[tuple[str | None, list[str]]] = []
    for b in doc.blocks:
        chunk: list[str] = []
        if b.text_plain and b.text_plain.strip():
            chunk.append(b.text_plain.strip())
        if not drop_media:
            for item in b.media:
                chunk.append(f"[{media_label(item)}]")
        if chunk:
            sender = b.sender.strip() if b.sender and b.sender.strip() else None
            if not groups or groups[-1][0] != sender:
                groups.append((sender, []))
            groups[-1][1].extend(chunk)

    parts = []
    for sender, lines in groups:
        parts.append(f"{sender}:\n" + "\n".join(lines) if sender else "\n".join(lines))
    return "\n\n".join(parts)
