"""Publish a CapturedDoc to telegra.ph.

Telegraph is the cheapest media-rich publish target: anonymous accounts, instant shareable
links, hosts images inline. Photos are uploaded to telegra.ph; other media degrade to a text
mention (Telegraph can't host arbitrary files). Per-user `access_token` is optional — without
one we mint a throwaway anonymous account.
"""

import json
from typing import Optional

import httpx

from app.models import CapturedDoc, MediaKind
from app.renderers.media import fetch_bytes
from app.renderers.util import media_label

_API = "https://api.telegra.ph"
_UPLOAD = "https://telegra.ph/upload"


async def _get_token(client: httpx.AsyncClient, author: str) -> str:
    r = await client.get(
        f"{_API}/createAccount",
        params={"short_name": author, "author_name": author},
    )
    r.raise_for_status()
    return r.json()["result"]["access_token"]


async def _upload_photo(client: httpx.AsyncClient, data: bytes) -> Optional[str]:
    try:
        r = await client.post(
            _UPLOAD, files={"file": ("photo.jpg", data, "image/jpeg")}, timeout=30
        )
        j = r.json()
        if isinstance(j, list) and j and "src" in j[0]:
            return "https://telegra.ph" + j[0]["src"]
    except Exception:
        return None
    return None


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
                src = None
                if item.kind == MediaKind.photo:
                    data = await fetch_bytes(item)
                    if data:
                        src = await _upload_photo(client, data)
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
                "title": (doc.title or "Captured messages")[:256],
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
