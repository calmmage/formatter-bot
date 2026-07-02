"""Build the text body for the 'post' format — one combined message/caption.

Two flavors: HTML (entities preserved, for a single caption/message that fits the limit) and
plaintext (for splitting across follow-up messages or attaching as a file, where broken tags
would be a risk). Both lead with the doc's display title.
"""

from app.models import CapturedDoc
from app.renderers.util import html_to_text


def _blocks_html(doc: CapturedDoc) -> str:
    parts = []
    for b in doc.blocks:
        if b.text_html and b.text_html.strip():
            parts.append(b.text_html.strip())
    return "\n\n".join(parts)


def post_caption_html(doc: CapturedDoc) -> str:
    """Combined HTML body with a bold title header."""
    import html as _html

    body = _blocks_html(doc)
    header = f"<b>{_html.escape(doc.display_title)}</b>"
    return f"{header}\n\n{body}".strip() if body else header


def post_plaintext(doc: CapturedDoc) -> str:
    """Combined plaintext body with a title header (for splitting / file attach)."""
    body = html_to_text(_blocks_html(doc)) or doc.text_excerpt
    return f"{doc.display_title}\n\n{body}".strip() if body else doc.display_title
