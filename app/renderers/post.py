"""Build the text body for the 'post' format — one combined message/caption.

Two flavors: HTML (entities preserved, for a single caption/message that fits the limit) and
plaintext (for splitting across follow-up messages or attaching as a file, where broken tags
would be a risk). Both lead with the doc's display title.
"""

import html as _html

from app.models import Block, CapturedDoc
from app.renderers.util import html_to_text


def _grouped_blocks(
    blocks: list[Block],
    *,
    text_attr: str,
    sender_html: bool = False,
) -> str:
    groups: list[tuple[str | None, list[str]]] = []
    for block in blocks:
        text = getattr(block, text_attr)
        if not text or not text.strip():
            continue
        sender = block.sender.strip() if block.sender and block.sender.strip() else None
        if not groups or groups[-1][0] != sender:
            groups.append((sender, []))
        groups[-1][1].append(text.strip())

    rendered = []
    for sender, lines in groups:
        if sender:
            label = _html.escape(sender) if sender_html else sender
            header = f"<b>{label}</b>:" if sender_html else f"{label}:"
            rendered.append(f"{header}\n" + "\n".join(lines))
        else:
            rendered.append("\n".join(lines))
    return "\n\n".join(rendered)


def post_caption_html(doc: CapturedDoc) -> str:
    """Combined HTML body with a bold title header."""
    body = _grouped_blocks(doc.blocks, text_attr="text_html", sender_html=True)
    header = f"<b>{_html.escape(doc.display_title)}</b>"
    return f"{header}\n\n{body}".strip() if body else header


def post_plaintext(doc: CapturedDoc) -> str:
    """Combined plaintext body with a title header (for splitting / file attach)."""
    body = html_to_text(_grouped_blocks(doc.blocks, text_attr="text_html")) or _grouped_blocks(
        doc.blocks,
        text_attr="text_plain",
    )
    return f"{doc.display_title}\n\n{body}".strip() if body else doc.display_title
