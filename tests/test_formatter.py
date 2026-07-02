"""Capture + renderer tests. Run with the project venv (needs botspot + pydantic)."""

import datetime
from types import SimpleNamespace

from app.capture import capture_batch
from app.models import Block, CapturedDoc, MediaItem, MediaKind
from app.renderers import render_markdown, render_plaintext
from app.renderers.util import html_to_markdown, html_to_text


def _fake_msg(mid, text, html=None):
    return SimpleNamespace(
        message_id=mid,
        date=datetime.datetime(2026, 1, 1, 9, 30),
        text=text,
        caption=None,
        html_text=html or text,
        from_user=SimpleNamespace(id=1, full_name="Alice"),
        forward_origin=None,
        photo=None,
        document=None,
        video=None,
        audio=None,
        voice=None,
        video_note=None,
    )


def test_capture_builds_ordered_blocks():
    doc = capture_batch([_fake_msg(1, "hello"), _fake_msg(2, "world")])
    assert isinstance(doc, CapturedDoc)
    assert [b.text_plain for b in doc.blocks] == ["hello", "world"]
    assert doc.user_id == 1
    assert doc.title == "hello"


def test_html_to_markdown_converts_entities():
    md = html_to_markdown('a <b>bold</b> <i>it</i> <a href="http://x.com">link</a> <code>c</code>')
    assert "**bold**" in md and "*it*" in md and "[link](http://x.com)" in md and "`c`" in md


def test_html_to_text_strips_tags():
    assert html_to_text("<b>hi</b> there") == "hi there"


def _doc_with_media():
    base = datetime.datetime(2026, 1, 1, 9, 30)
    return CapturedDoc(
        user_id=1,
        created_at=base,
        blocks=[
            Block(message_id=1, ts=base, sender="Alice", text_html="hi", text_plain="hi"),
            Block(
                message_id=2,
                ts=base,
                sender="Alice",
                media=[MediaItem(kind=MediaKind.document, file_id="D1", file_name="a.pdf")],
            ),
        ],
    )


def test_plaintext_media_mention_vs_drop():
    doc = _doc_with_media()
    assert "a.pdf" in render_plaintext(doc)
    assert "a.pdf" not in render_plaintext(doc, drop_media=True)


def test_markdown_includes_media_reference_and_title():
    out = render_markdown(_doc_with_media())
    assert out.startswith("# ")
    assert "a.pdf" in out


# --- title override / display_title ---


def test_display_title_prefers_override():
    doc = _doc_with_media()
    assert doc.display_title == doc.title  # heuristic before generation
    doc.title_override = "A Snappy Headline"
    assert doc.display_title == "A Snappy Headline"
    assert render_markdown(doc).startswith("# A Snappy Headline")


def test_text_excerpt_joins_blocks():
    base = datetime.datetime(2026, 1, 1, 9, 30)
    doc = CapturedDoc(
        user_id=1,
        created_at=base,
        blocks=[
            Block(message_id=1, ts=base, text_plain="first"),
            Block(message_id=2, ts=base, text_plain="second"),
        ],
    )
    assert doc.text_excerpt == "first\n\nsecond"


# --- post text builder ---


def test_post_caption_html_leads_with_bold_title():
    from app.renderers.post import post_caption_html, post_plaintext

    doc = _doc_with_media()
    doc.title_override = "My Title"
    html = post_caption_html(doc)
    assert html.startswith("<b>My Title</b>")
    assert "hi" in html
    assert post_plaintext(doc).startswith("My Title")


# --- post media partitioning ---


def test_runs_split_by_type_and_cap():
    from app.post import _runs

    photos = [MediaItem(kind=MediaKind.photo, file_id=f"P{i}") for i in range(12)]
    docs = [MediaItem(kind=MediaKind.document, file_id="D1", file_name="a.pdf")]
    voice = [MediaItem(kind=MediaKind.voice, file_id="V1")]
    runs = _runs(photos + docs + voice)
    # 12 photos -> 10 + 2, then a doc run, then voice singly
    assert [len(r) for r in runs] == [10, 2, 1, 1]
    # photos never share a run with the document
    assert all(m.kind == MediaKind.photo for m in runs[0])
    assert runs[2][0].kind == MediaKind.document
    assert runs[3][0].kind == MediaKind.voice


# --- telegraph image host seam ---


def test_telegraph_uses_image_host(monkeypatch):
    import asyncio

    from app.exporters import imagehost, telegraph

    class FakeHost:
        async def upload(self, data, *, filename, mime):
            return "https://nas.example/img/1.jpg"

    async def fake_fetch(item):
        return b"bytes"

    monkeypatch.setattr(telegraph, "fetch_bytes", fake_fetch)
    imagehost.set_image_host(FakeHost())
    try:
        item = MediaItem(kind=MediaKind.photo, file_id="P1")
        src = asyncio.run(telegraph._host_image(item))
        assert src == "https://nas.example/img/1.jpg"
    finally:
        imagehost.set_image_host(None)

    # with no host configured, photo hosting returns None (degrades to text mention)
    assert asyncio.run(telegraph._host_image(MediaItem(kind=MediaKind.photo, file_id="P2"))) is None
