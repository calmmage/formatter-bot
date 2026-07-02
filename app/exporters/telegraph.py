"""Publish a CapturedDoc to telegra.ph.

Telegraph gives anonymous accounts + instant shareable links and renders images by URL. Its own
upload endpoint (telegra.ph/upload) was discontinued and now 400s for every image, so photos are
routed through a pluggable ImageHost (see exporters/imagehost.py). With no host configured,
media degrades to a text mention. Per-user `access_token` is optional — without one we mint a
throwaway anonymous account.
"""

import json
from typing import Optional

import httpx

from app.exporters.imagehost import get_image_host
from app.models import CapturedDoc, MediaItem, MediaKind
from app.renderers.media import fetch_bytes, mime_for
from app.renderers.util import media_label

_API = "https://api.telegra.ph"


async def _get_token(client: httpx.AsyncClient, author: str) -> str:
    r = await client.get(
        f"{_API}/createAccount",
        params={"short_name": author, "author_name": author},
    )
    r.raise_for_status()
    return r.json()["result"]["access_token"]


async def _host_image(item: MediaItem) -> Optional[str]:
    """Upload a photo via the configured image host and return its public URL."""
    host = get_image_host()
    if host is None:
        return None
    data = await fetch_bytes(item)
    if not data:
        return None
    return await host.upload(
        data, filename=item.file_name or "photo.jpg", mime=mime_for(item)
    )


async def publish_telegraph(
    doc: CapturedDoc,
    access_token: Optional[str] = None,
    author_name: str = "formatter-bot",
) -> str:
    """Publish and return the page URL."""
    async with httpx.AsyncClient(timeout=60) as client:
        token = access_token or await _get_token(client, author_name)

        nodes: list = []
        for b in doc.blocks:
            if b.text_plain and b.text_plain.strip():
                nodes.append({"tag": "p", "children": [b.text_plain.strip()]})
            for item in b.media:
                src = await _host_image(item) if item.kind == MediaKind.photo else None
                if src:
                    nodes.append({"tag": "figure", "children": [{"tag": "img", "attrs": {"src": src}}]})
                else:
                    nodes.append({"tag": "p", "children": [f"[{media_label(item)}]"]})

        if not nodes:
            nodes = [{"tag": "p", "children": ["(empty)"]}]

        r = await client.post(
            f"{_API}/createPage",
            data={
                "access_token": token,
                "title": (doc.display_title or "Captured messages")[:256],
                "author_name": author_name,
                "content": json.dumps(nodes),
                "return_content": "false",
            },
        )
        r.raise_for_status()
        j = r.json()
        if not j.get("ok"):
            raise RuntimeError(j.get("error", "telegraph error"))
        return j["result"]["url"]
