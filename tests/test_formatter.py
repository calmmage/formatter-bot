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
