"""In-memory per-user state: the last captured document + format preferences.

MVP storage. The canonical doc holds Telegram file_ids (not bytes), so it's cheap to keep in
memory; media is re-fetched lazily at render time. Persisting docs to mongo (survive restarts)
is a planned follow-up — see notes-ai.
"""

from typing import Dict, Optional

from app.models import CapturedDoc

_last_doc: Dict[int, CapturedDoc] = {}

_DEFAULT_PREFS = {
    "default_format": None,  # if set, auto-render on capture instead of showing the menu
    "drop_media": False,  # plaintext: drop media entirely vs mention it
    "telegraph_token": None,  # per-user telegra.ph account token
}
_prefs: Dict[int, dict] = {}


def save_doc(user_id: int, doc: CapturedDoc) -> None:
    _last_doc[user_id] = doc


def get_doc(user_id: int) -> Optional[CapturedDoc]:
    return _last_doc.get(user_id)


def get_prefs(user_id: int) -> dict:
    return {**_DEFAULT_PREFS, **_prefs.get(user_id, {})}


def set_pref(user_id: int, key: str, value) -> None:
    _prefs.setdefault(user_id, {})[key] = value
