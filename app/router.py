from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from botspot import get_message_aggregator
from botspot.commands_menu import add_command
from botspot.utils import send_safe

from app._app import App
from app.capture import capture_batch
from app.formats import FORMATS, produce
from app.store import get_doc, get_prefs, save_doc

router = Router()
app = App()


def _format_keyboard() -> InlineKeyboardMarkup:
    rows, row = [], []
    for key, (label, _) in FORMATS.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"fmt:{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


@add_command("start", "Start the bot")
@router.message(CommandStart())
async def start_handler(message: Message):
    await send_safe(
        message.chat.id,
        f"👋 Welcome to <b>{app.name}</b>.\n\n"
        "Forward me a pile of messages — text, photos, albums, files, voice — and I'll "
        "capture them as one document you can re-emit in different formats.\n\n"
        "Send some messages, then pick a format. /help for details.",
    )


@add_command("help", "How it works")
@router.message(Command("help"))
async def help_handler(message: Message):
    fmt_lines = "\n".join(f"• {label}" for label, _ in FORMATS.values())
    await send_safe(
        message.chat.id,
        "📥 <b>Capture:</b> forward/send a burst of messages (albums included). I group them "
        "into one document.\n\n"
        f"🎚 <b>Formats:</b>\n{fmt_lines}\n\n"
        "Commands:\n"
        "/format — re-format the last captured batch\n"
        "/settings — default format, media handling, Telegraph token",
    )


@add_command("format", "Re-format the last captured batch")
@router.message(Command("format"))
async def format_handler(message: Message):
    doc = get_doc(message.from_user.id)
    if not doc:
        await send_safe(message.chat.id, "Nothing captured yet — forward me some messages first.")
        return
    await send_safe(
        message.chat.id,
        f"Pick a format for the last <b>{len(doc.blocks)}</b> message(s):",
        reply_markup=_format_keyboard(),
    )


@router.message()
async def capture_handler(message: Message):
    # defensive: let commands fall through to their handlers
    if message.text and message.text.startswith("/"):
        return
    batch = await get_message_aggregator().collect(message)
    if batch is None:
        return  # folded into a batch an earlier call owns

    doc = capture_batch(batch)
    uid = message.from_user.id if message.from_user else message.chat.id
    save_doc(uid, doc)

    prefs = get_prefs(uid)
    if prefs.get("default_format") in FORMATS:
        await _emit(message, prefs["default_format"], doc, prefs)
        return

    await send_safe(
        message.chat.id,
        f"📥 Captured <b>{len(doc.blocks)}</b> message(s) · {doc.n_media} media. Format as:",
        reply_markup=_format_keyboard(),
    )


@router.callback_query(F.data.startswith("fmt:"))
async def on_format(cb: CallbackQuery):
    key = cb.data.split(":", 1)[1]
    doc = get_doc(cb.from_user.id)
    if not doc:
        await cb.answer("Nothing captured — forward messages first.", show_alert=True)
        return
    if key not in FORMATS:
        await cb.answer("Unknown format.")
        return
    await cb.answer(f"Rendering {key}…")
    await _emit(cb.message, key, doc, get_prefs(cb.from_user.id))


async def _emit(message: Message, key: str, doc, prefs: dict) -> None:
    try:
        out = await produce(key, doc, prefs)
    except Exception as e:
        await send_safe(message.chat.id, f"⚠️ Failed to produce {key}: {e}")
        return
    if out.kind == "file" and out.data is not None:
        await message.answer_document(
            BufferedInputFile(out.data, filename=out.filename or "capture.txt"),
            caption=f"{FORMATS[key][0]} · {doc.title}",
        )
    elif out.text:
        await send_safe(message.chat.id, out.text)
