"""Markdown renderer — entities preserved (bold/italic/links/code), media as references."""

from app.models import CapturedDoc
from app.renderers.util import html_to_markdown, media_label


def render_markdown(doc: CapturedDoc) -> str:
    parts = [f"# {doc.title}", ""]
    for b in doc.blocks:
        ts = b.ts.strftime("%H:%M")
        meta = " · ".join(p for p in (b.sender, ts) if p)
        if meta:
            parts.append(f"**{meta}**")
        if b.text_html:
            parts.append(html_to_markdown(b.text_html))
        for item in b.media:
            parts.append(f"_{media_label(item)}_")
        parts.append("")
    return "\n".join(parts).strip() + "\n"
