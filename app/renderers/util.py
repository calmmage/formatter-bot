"""Tiny, dependency-free converters from Telegram-HTML to markdown / plaintext.

Telegram only emits a small, fixed tag set (b, strong, i, em, u, s, code, pre, a, br, blockquote),
so a handful of regexes covers it without pulling in a full HTML parser.
"""

import html as _html
import re

_TAG = re.compile(r"<[^>]+>")
_A = re.compile(r'<a\s+href="([^"]*)"\s*>(.*?)</a>', re.DOTALL | re.IGNORECASE)


def _unescape(text: str) -> str:
    return _html.unescape(text)


def html_to_markdown(html: str) -> str:
    if not html:
        return ""
    s = html.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    s = _A.sub(r"[\2](\1)", s)
    for tag, md in (("b", "**"), ("strong", "**"), ("i", "*"), ("em", "*"), ("s", "~~")):
        s = re.sub(rf"<{tag}>(.*?)</{tag}>", rf"{md}\1{md}", s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r"<pre>(.*?)</pre>", r"```\n\1\n```", s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r"<code>(.*?)</code>", r"`\1`", s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(
        r"<blockquote>(.*?)</blockquote>",
        lambda m: "\n".join("> " + ln for ln in m.group(1).splitlines()),
        s,
        flags=re.DOTALL | re.IGNORECASE,
    )
    s = _TAG.sub("", s)  # drop anything left (u, spoilers, etc.)
    return _unescape(s).strip()


_MEDIA_EMOJI = {
    "photo": "📷",
    "video": "🎬",
    "video_note": "🎬",
    "audio": "🎵",
    "voice": "🎤",
    "document": "📎",
}


def media_label(item) -> str:
    """Human label for a media item, e.g. '📷 photo' or '📎 report.pdf'."""
    kind = item.kind.value if hasattr(item.kind, "value") else str(item.kind)
    emoji = _MEDIA_EMOJI.get(kind, "📦")
    name = item.file_name or kind.replace("_", " ")
    return f"{emoji} {name}"


def html_to_text(html: str) -> str:
    if not html:
        return ""
    s = html.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    s = _A.sub(r"\2 (\1)", s)
    s = _TAG.sub("", s)
    return _unescape(s).strip()
