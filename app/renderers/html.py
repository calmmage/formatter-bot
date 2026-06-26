"""HTML renderer — a single self-contained file with media inlined as data URIs."""

import base64
import html as _html

from app.models import Block, CapturedDoc, MediaItem, MediaKind
from app.renderers.media import fetch_bytes, mime_for
from app.renderers.util import media_label

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ max-width: 720px; margin: 2rem auto; padding: 0 1rem;
         font: 16px/1.6 -apple-system, system-ui, sans-serif; color: #1a1a1a; }}
  .block {{ padding: .75rem 0; border-bottom: 1px solid #eee; }}
  .meta {{ color: #888; font-size: .8rem; margin-bottom: .25rem; }}
  img, video {{ max-width: 100%; border-radius: 8px; margin: .5rem 0; }}
  pre {{ background: #f6f6f6; padding: .5rem; border-radius: 6px; overflow-x: auto; }}
  a.file {{ display: inline-block; margin: .25rem 0; }}
</style></head><body>
<h1>{title}</h1>
{body}
</body></html>
"""


async def _media_html(item: MediaItem) -> str:
    data = await fetch_bytes(item)
    label = _html.escape(media_label(item))
    if data is None:
        return f'<p>⚠️ [{label} — unavailable]</p>'
    b64 = base64.b64encode(data).decode()
    uri = f"data:{mime_for(item)};base64,{b64}"
    if item.kind == MediaKind.photo:
        return f'<img src="{uri}" alt="{label}">'
    if item.kind in (MediaKind.video, MediaKind.video_note):
        return f'<video controls src="{uri}"></video>'
    if item.kind in (MediaKind.audio, MediaKind.voice):
        return f'<audio controls src="{uri}"></audio>'
    fname = _html.escape(item.file_name or "file")
    return f'<a class="file" href="{uri}" download="{fname}">⬇️ {label}</a>'


async def _block_html(b: Block) -> str:
    ts = b.ts.strftime("%H:%M")
    meta = " · ".join(p for p in (b.sender, ts) if p)
    parts = [f'<div class="meta">{_html.escape(meta)}</div>'] if meta else []
    if b.text_html:
        parts.append(f"<div>{b.text_html}</div>")
    for item in b.media:
        parts.append(await _media_html(item))
    return f'<div class="block">{"".join(parts)}</div>'


async def render_html(doc: CapturedDoc) -> str:
    title = _html.escape(doc.title)
    body = "\n".join([await _block_html(b) for b in doc.blocks])
    return _PAGE.format(title=title, body=body)
