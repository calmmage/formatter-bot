"""LLM-generated titles for a captured doc, in a handful of styles.

Uses botspot's LLM provider (enabled via BOTSPOT_LLM_PROVIDER_ENABLED) so the model + key stay
framework-managed. The style is user-picked via buttons; each maps to a one-line instruction.
"""

from typing import Dict, Tuple

from botspot.components.new.llm_provider import aquery_llm_text

from app.models import CapturedDoc

# key -> (button label, instruction fed to the model)
STYLES: Dict[str, Tuple[str, str]] = {
    "concise": ("✂️ Concise", "a short, plain title of 3-6 words"),
    "descriptive": ("📋 Descriptive", "a clear one-line descriptive title, up to ~12 words"),
    "catchy": ("✨ Catchy", "a catchy, engaging headline"),
    "emoji": ("😀 Emoji", "a short title that begins with one relevant emoji"),
}

_MAX_SOURCE = 2000  # chars of the doc fed to the model


def _source(doc: CapturedDoc) -> str:
    body = doc.text_excerpt[:_MAX_SOURCE]
    if doc.n_media:
        body = f"[{doc.n_media} media attachment(s)]\n{body}".strip()
    return body or "(media-only, no text)"


async def generate_title(doc: CapturedDoc, style: str) -> str:
    """Generate a title in the requested style. Returns a clean single line."""
    instr = STYLES.get(style, STYLES["concise"])[1]
    prompt = (
        f"Write {instr} for the captured content below. "
        "Return ONLY the title text — no quotes, no preamble, no trailing punctuation.\n\n"
        f"---\n{_source(doc)}\n---"
    )
    text = await aquery_llm_text(
        prompt,
        system_message="You write short, accurate titles for captured message threads.",
        max_tokens=40,
    )
    title = (text or "").strip().strip("\"'").splitlines()[0] if text else ""
    return title[:100] or doc.title
