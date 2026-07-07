"""Markdown renderer — entities preserved (bold/italic/links/code), media as references."""

from app.models import CapturedDoc
from app.renderers.util import html_to_markdown, media_label


def render_markdown(doc: CapturedDoc) -> str:
    parts = [f"# {doc.display_title}", ""]
    groups: list[tuple[str | None, list[str]]] = []
    for b in doc.blocks:
        chunk: list[str] = []
        if b.text_html:
            chunk.append(html_to_markdown(b.text_html))
        for item in b.media:
            chunk.append(f"_{media_label(item)}_")
        if chunk:
            sender = b.sender.strip() if b.sender and b.sender.strip() else None
            if not groups or groups[-1][0] != sender:
                groups.append((sender, []))
            groups[-1][1].extend(chunk)
    for sender, lines in groups:
        if sender:
            parts.append(f"**{sender}:**")
        parts.extend(lines)
        parts.append("")
    return "\n".join(parts).strip() + "\n"
