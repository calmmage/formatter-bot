"""Plaintext renderer — formatting stripped, media mentioned (or dropped)."""

from app.models import CapturedDoc
from app.renderers.util import media_label


def render_plaintext(doc: CapturedDoc, drop_media: bool = False) -> str:
    parts = []
    for b in doc.blocks:
        chunk = []
        ts = b.ts.strftime("[%H:%M]")
        header = " ".join(p for p in (ts, b.sender) if p)
        if b.text_plain and b.text_plain.strip():
            chunk.append(f"{header}\n{b.text_plain.strip()}" if header else b.text_plain.strip())
        elif header:
            chunk.append(header)
        if not drop_media:
            for item in b.media:
                chunk.append(f"[{media_label(item)}]")
        if chunk:
            parts.append("\n".join(chunk))
    return "\n\n".join(parts)
