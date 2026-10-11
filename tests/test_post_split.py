"""Regression: choosing "Split into messages" must not attach the text as a file.

send_safe's default (send_long_messages_as_files=True) turns anything over 4096
chars into a timestamped .txt. The overflow menu's split choice has to bypass that.
"""

import asyncio
import datetime
from types import SimpleNamespace

from app.models import Block, CapturedDoc, MediaItem, MediaKind
from app.post import send_as_post

LONG = "word " * 1200  # 6000 chars, over both the 1024 caption cap and the 4096 message cap


class _Bot:
    def __init__(self):
        self.messages: list[str] = []
        self.documents: list[str] = []
        self.photos: list[str] = []

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append(text)
        assert kwargs.get("parse_mode") is None

    async def send_document(self, chat_id, document, **kwargs):
        name = getattr(document, "filename", None) or "document"
        self.documents.append(name)

    async def send_photo(self, chat_id, file_id, **kwargs):
        self.photos.append(file_id)

    async def send_media_group(self, chat_id, media, **kwargs):
        raise AssertionError("single photo should not go out as an album")


def _doc(*, with_photo: bool) -> CapturedDoc:
    base = datetime.datetime(2026, 10, 11, 15, 21)
    media = [MediaItem(kind=MediaKind.photo, file_id="PHOTO")] if with_photo else []
    return CapturedDoc(
        user_id=1,
        created_at=base,
        blocks=[
            Block(
                message_id=1,
                ts=base,
                sender="Alice",
                text_plain=LONG,
                text_html=LONG,
                media=media,
            )
        ],
    )


def _run(choice: str, *, with_photo: bool):
    bot = _Bot()
    sent_safe: list[str] = []

    async def ask_user_choice(*args, **kwargs):
        return choice

    async def send_safe(chat_id, text, **kwargs):
        sent_safe.append(text)
        return SimpleNamespace()

    async def go():
        import app.post as post

        post.ask_user_choice = ask_user_choice
        post.get_bot = lambda: bot
        post.send_safe = send_safe
        message = SimpleNamespace(chat=SimpleNamespace(id=42))
        await send_as_post(message, _doc(with_photo=with_photo), {}, state=None)

    asyncio.run(go())
    return bot, sent_safe


def test_split_with_media_sends_chunks_not_a_file():
    bot, sent_safe = _run("split", with_photo=True)

    assert bot.photos == ["PHOTO"]
    assert bot.documents == []
    assert sent_safe == []
    assert len(bot.messages) >= 2
    assert all(len(part) <= 4096 for part in bot.messages)
    assert LONG[:100] in "\n".join(bot.messages)


def test_split_without_media_sends_chunks_not_a_file():
    bot, sent_safe = _run("split", with_photo=False)

    assert bot.documents == []
    assert sent_safe == []
    assert len(bot.messages) >= 2
    assert all(len(part) <= 4096 for part in bot.messages)


def test_file_choice_still_attaches_post_md():
    bot, sent_safe = _run("file", with_photo=True)

    assert bot.documents == ["post.md"]
    assert bot.messages == []
    assert sent_safe == []
