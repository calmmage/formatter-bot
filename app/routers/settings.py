from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from botspot.commands_menu import add_command
from botspot.user_interactions import ask_user, ask_user_choice
from botspot.utils import send_safe

from app.formats import FORMATS
from app.store import get_prefs, set_pref

router = Router()

_SETTINGS = [
    "Default format (auto-render on capture)",
    "Plaintext: drop vs mention media",
    "Set Telegraph access token",
    "Show current settings",
]


@add_command("settings", "Configure formats & integrations")
@router.message(Command("settings"))
async def settings_menu(message: Message, state) -> None:
    uid = message.from_user.id
    choice = await ask_user_choice(message.chat.id, "Formatter settings:", _SETTINGS, state)
    if not choice:
        return

    if choice == _SETTINGS[0]:
        options = ["(none — always ask)"] + [label for label, _ in FORMATS.values()]
        picked = await ask_user_choice(message.chat.id, "Default format:", options, state)
        if not picked:
            return
        if picked == options[0]:
            set_pref(uid, "default_format", None)
            await send_safe(message.chat.id, "Default format cleared — I'll show the menu each time.")
        else:
            key = next(k for k, (label, _) in FORMATS.items() if label == picked)
            set_pref(uid, "default_format", key)
            await send_safe(message.chat.id, f"Default format set to {picked}.")

    elif choice == _SETTINGS[1]:
        picked = await ask_user_choice(
            message.chat.id, "In plaintext, media should be:", ["Mentioned", "Dropped"], state
        )
        if not picked:
            return
        set_pref(uid, "drop_media", picked == "Dropped")
        await send_safe(message.chat.id, f"Plaintext media: {picked.lower()}.")

    elif choice == _SETTINGS[2]:
        token = await ask_user(
            message.chat.id,
            "Paste your telegra.ph access token (or 'clear' to remove). "
            "Leave empty to keep using anonymous pages.",
            state,
        )
        if token is None:
            return
        token = token.strip()
        set_pref(uid, "telegraph_token", None if token.lower() in ("", "clear") else token)
        await send_safe(message.chat.id, "Telegraph token updated.")

    elif choice == _SETTINGS[3]:
        p = get_prefs(uid)
        default = p["default_format"] or "ask each time"
        media = "dropped" if p["drop_media"] else "mentioned"
        tg = "set" if p["telegraph_token"] else "anonymous"
        await send_safe(
            message.chat.id,
            f"<b>Your settings</b>\n"
            f"• Default format: {default}\n"
            f"• Plaintext media: {media}\n"
            f"• Telegraph token: {tg}",
        )
