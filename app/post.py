"""Re-emit a captured doc as a single Telegram post: media album(s) + combined text.

This is the media-carrying output. Media is resent by file_id (no re-download). Telegram caps:
albums are 2-10 items and can't mix photos/videos with documents or audio, so we send typed
runs; captions cap at ~1024 chars, plain messages at ~4096. Overflow (too many media / too much
text) is resolved interactively via buttons rather than silently truncating.
"""

from typing import List, Optional

from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
)
from botspot.user_interactions import ask_user_choice
from botspot.utils import get_bot, send_safe

from app.models import CapturedDoc, MediaItem, MediaKind
from app.renderers.markdown import render_markdown
from app.renderers.post import post_caption_html, post_plaintext

MEDIAGROUP_MAX = 10
CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096
# Thresholds at which we ask the user how to handle overflow (per the product spec).
TEXT_ASK_WITH_MEDIA = 1000
TEXT_ASK_PLAIN = 4000

_ALBUMABLE = {MediaKind.photo, MediaKind.video}
_INPUT = {
    MediaKind.photo: InputMediaPhoto,
    MediaKind.video: InputMediaVideo,
    MediaKind.document: InputMediaDocument,
    MediaKind.audio: InputMediaAudio,
}


def _chunk(items: List[MediaItem], n: int = MEDIAGROUP_MAX) -> List[List[MediaItem]]:
    return [items[i : i + n] for i in range(0, len(items), n)]


def _runs(media: List[MediaItem]) -> List[List[MediaItem]]:
    """Split media into send-groups Telegram will accept (typed, <=10 each)."""
    albumable = [m for m in media if m.kind in _ALBUMABLE]
    docs = [m for m in media if m.kind == MediaKind.document]
    audios = [m for m in media if m.kind == MediaKind.audio]
    singles = [m for m in media if m.kind in (MediaKind.voice, MediaKind.video_note)]
    runs: List[List[MediaItem]] = []
    for group in (albumable, docs, audios):
        runs.extend(_chunk(group))
    runs.extend([m] for m in singles)  # voice / video_note go one at a time
    return runs


async def _send_run(bot, chat_id: int, run: List[MediaItem], caption: Optional[str]) -> None:
    """Send one group; caption (HTML) goes on the first item, if the type supports it."""
    if len(run) == 1:
        m = run[0]
        kw = dict(caption=caption, parse_mode="HTML") if caption else {}
        if m.kind == MediaKind.photo:
            await bot.send_photo(chat_id, m.file_id, **kw)
        elif m.kind == MediaKind.video:
            await bot.send_video(chat_id, m.file_id, **kw)
        elif m.kind == MediaKind.document:
            await bot.send_document(chat_id, m.file_id, **kw)
        elif m.kind == MediaKind.audio:
            await bot.send_audio(chat_id, m.file_id, **kw)
        elif m.kind == MediaKind.voice:
            await bot.send_voice(chat_id, m.file_id, **kw)
        elif m.kind == MediaKind.video_note:
            await bot.send_video_note(chat_id, m.file_id)  # no caption support
        return
    inputs = []
    for i, m in enumerate(run):
        cls = _INPUT[m.kind]
        if i == 0 and caption:
            inputs.append(cls(media=m.file_id, caption=caption, parse_mode="HTML"))
        else:
            inputs.append(cls(media=m.file_id))
    await bot.send_media_group(chat_id, inputs)


async def send_as_post(message, doc: CapturedDoc, prefs: dict, state: FSMContext) -> None:
    """Emit the doc as a Telegram post, resolving overflow interactively."""
    bot = get_bot()
    chat_id = message.chat.id
    media = [item for b in doc.blocks for item in b.media]

    # --- media overflow: too many for a single album ---
    if len(media) > MEDIAGROUP_MAX:
        pick = await ask_user_choice(
            chat_id,
            f"📎 {len(media)} media — Telegram albums hold {MEDIAGROUP_MAX}. Cut down?",
            {"cut": f"First {MEDIAGROUP_MAX} only", "all": "Send all (multiple albums)"},
            state,
        )
        if pick is None:
            return
        if pick == "cut":
            media = media[:MEDIAGROUP_MAX]

    has_media = bool(media)
    plain = post_plaintext(doc)
    cap_limit = CAPTION_LIMIT if has_media else MESSAGE_LIMIT
    ask_at = TEXT_ASK_WITH_MEDIA if has_media else TEXT_ASK_PLAIN

    # --- text overflow: too long to ride along as a caption / single message ---
    text_mode = "inline"
    if len(plain) > ask_at:
        pick = await ask_user_choice(
            chat_id,
            f"📝 Text is {len(plain)} chars (limit ~{cap_limit}). How should I send it?",
            {
                "file": "Attach full text as file",
                "split": "Split into messages",
                "trim": "Trim to fit",
            },
            state,
        )
        if pick is None:
            return
        text_mode = pick

    # Decide the caption that rides on the media (if any).
    caption_html: Optional[str] = None
    if has_media:
        if text_mode == "inline":
            caption_html = post_caption_html(doc)
        elif text_mode == "trim":
            caption_html = None  # trimmed plaintext caption handled below
    runs = _runs(media)

    trimmed_caption: Optional[str] = None
    if has_media and text_mode == "trim":
        trimmed_caption = plain[: cap_limit - 1] + "…" if len(plain) > cap_limit else plain

    # --- send media ---
    caption_used = False
    for run in runs:
        cap = None
        if not caption_used:
            if caption_html is not None:
                cap = caption_html
                caption_used = True
            elif trimmed_caption is not None:
                # plaintext caption: send with no HTML parse to avoid entity issues
                await _send_run_plain_caption(bot, chat_id, run, trimmed_caption)
                caption_used = True
                continue
        await _send_run(bot, chat_id, run, cap)

    # --- send text that didn't ride the media ---
    if not has_media:
        if text_mode == "file":
            await _send_text_file(bot, chat_id, doc)
        else:  # inline or split — send_safe auto-splits long text
            await send_safe(chat_id, post_caption_html(doc))
        return

    # media present:
    if text_mode == "file":
        await _send_text_file(bot, chat_id, doc)
    elif text_mode == "split":
        await send_safe(chat_id, plain)  # auto-split into <=4096 chunks
    elif text_mode == "inline" and not caption_used:
        # media types couldn't hold a caption (e.g. only video notes) — send text separately
        await send_safe(chat_id, post_caption_html(doc))


async def _send_run_plain_caption(bot, chat_id: int, run: List[MediaItem], caption: str) -> None:
    if len(run) == 1:
        m = run[0]
        if m.kind == MediaKind.photo:
            await bot.send_photo(chat_id, m.file_id, caption=caption)
            return
        if m.kind == MediaKind.video:
            await bot.send_video(chat_id, m.file_id, caption=caption)
            return
    inputs = []
    for i, m in enumerate(run):
        cls = _INPUT[m.kind]
        inputs.append(cls(media=m.file_id, caption=caption) if i == 0 else cls(media=m.file_id))
    await bot.send_media_group(chat_id, inputs)


async def _send_text_file(bot, chat_id: int, doc: CapturedDoc) -> None:
    data = render_markdown(doc).encode()
    await bot.send_document(
        chat_id,
        BufferedInputFile(data, filename="post.md"),
        caption=f"📝 {doc.display_title}",
    )
