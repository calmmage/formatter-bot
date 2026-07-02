from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
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
from app.formats import FORMATS, POST_KEY, produce
from app.post import send_as_post
from app.store import get_doc, get_prefs, save_doc
from app.titler import STYLES, generate_title

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
    rows.append([InlineKeyboardButton(text="🏷 Title (AI)", callback_data="title:")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _title_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"titlestyle:{key}")]
        for key, (label, _) in STYLES.items()
    ]
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
        "🏷 <b>Title:</b> tap <i>Title (AI)</i> to generate a headline in a style you pick.\n\n"
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
async def capture_handler(message: Message, state: FSMContext):
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
    default = prefs.get("default_format")
    if default in FORMATS:
        await _dispatch(message, default, doc, prefs, state)
        return

    await send_safe(
        message.chat.id,
        f"📥 Captured <b>{len(doc.blocks)}</b> message(s) · {doc.n_media} media. Format as:",
        reply_markup=_format_keyboard(),
    )


@router.callback_query(F.data.startswith("fmt:"))
async def on_format(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":", 1)[1]
    doc = get_doc(cb.from_user.id)
    if not doc:
        await cb.answer("Nothing captured — forward messages first.", show_alert=True)
        return
    if key not in FORMATS:
        await cb.answer("Unknown format.")
        return
    await cb.answer(f"Rendering {key}…")
    await _dispatch(cb.message, key, doc, get_prefs(cb.from_user.id), state)


@router.callback_query(F.data == "title:")
async def on_title(cb: CallbackQuery):
    if not get_doc(cb.from_user.id):
        await cb.answer("Nothing captured — forward messages first.", show_alert=True)
        return
    await cb.answer()
    await cb.message.answer("🏷 Pick a title style:", reply_markup=_title_keyboard())


@router.callback_query(F.data.startswith("titlestyle:"))
async def on_title_style(cb: CallbackQuery):
    style = cb.data.split(":", 1)[1]
    doc = get_doc(cb.from_user.id)
    if not doc:
        await cb.answer("Nothing captured — forward messages first.", show_alert=True)
        return
    await cb.answer("Generating title…")
    try:
        title = await generate_title(doc, style)
    except Exception as e:
        await send_safe(cb.message.chat.id, f"⚠️ Couldn't generate a title: {e}")
        return
    doc.title_override = title  # stored doc is mutated in place
    await send_safe(
        cb.message.chat.id,
        f"🏷 <b>{title}</b>\n\nUsed as the title for post / Telegraph / file outputs.",
        reply_markup=_format_keyboard(),
    )


async def _dispatch(message: Message, key: str, doc, prefs: dict, state: FSMContext) -> None:
    if key == POST_KEY:
        try:
            await send_as_post(message, doc, prefs, state)
        except Exception as e:
            await send_safe(message.chat.id, f"⚠️ Failed to build the post: {e}")
        return
    await _emit(message, key, doc, prefs)


async def _emit(message: Message, key: str, doc, prefs: dict) -> None:
    try:
        out = await produce(key, doc, prefs)
    except Exception as e:
        await send_safe(message.chat.id, f"⚠️ Failed to produce {key}: {e}")
        return
    if out.kind == "file" and out.data is not None:
        await message.answer_document(
            BufferedInputFile(out.data, filename=out.filename or "capture.txt"),
            caption=f"{FORMATS[key][0]} · {doc.display_title}",
        )
    elif out.text:
        await send_safe(message.chat.id, out.text)
