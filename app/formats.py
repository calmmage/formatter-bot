"""Format registry — maps a format key to a label and a producer over the canonical doc.

Add a format = add an entry here. Producers return an `Output` the router knows how to send
(a file to upload, or a text reply such as a published link).
"""

from dataclasses import dataclass
from typing import Optional

from app.exporters import publish_telegraph
from app.models import CapturedDoc
from app.renderers import render_html, render_markdown, render_plaintext


@dataclass
class Output:
    kind: str  # "file" | "text"
    filename: Optional[str] = None
    data: Optional[bytes] = None
    text: Optional[str] = None


async def _markdown(doc: CapturedDoc, prefs: dict) -> Output:
    return Output("file", "capture.md", render_markdown(doc).encode())


async def _html(doc: CapturedDoc, prefs: dict) -> Output:
    return Output("file", "capture.html", (await render_html(doc)).encode())


async def _plaintext(doc: CapturedDoc, prefs: dict) -> Output:
    text = render_plaintext(doc, drop_media=prefs.get("drop_media", False))
    return Output("file", "capture.txt", text.encode())


async def _telegraph(doc: CapturedDoc, prefs: dict) -> Output:
    url = await publish_telegraph(doc, access_token=prefs.get("telegraph_token"))
    return Output("text", text=f"📰 Published to Telegraph:\n{url}")


# key -> (button label, producer). Order defines keyboard order.
FORMATS = {
    "markdown": ("📝 Markdown", _markdown),
    "html": ("🌐 HTML", _html),
    "plaintext": ("📄 Plaintext", _plaintext),
    "telegraph": ("📰 Telegraph", _telegraph),
}


def labels() -> dict:
    return {k: v[0] for k, v in FORMATS.items()}


async def produce(key: str, doc: CapturedDoc, prefs: dict) -> Output:
    _, fn = FORMATS[key]
    return await fn(doc, prefs)
