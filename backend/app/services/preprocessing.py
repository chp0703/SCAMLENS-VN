"""Stateless text normalization shared by offline preparation and inference."""

import re
import unicodedata

RULES_VERSION = "1.0.0"
TOKENS = ("URL", "PHONE", "EMAIL", "NUMBER", "BANK_ACC", "MONEY", "TIME", "DATE", "NAME", "POINT")
_TOKEN = re.compile(r"\[(?:" + "|".join(TOKENS) + r")\]", re.IGNORECASE)
_URL = re.compile(r"(?<![\w@])(?:https?://|www\.)[^\s<>\[\]\"'\U0001f000-\U0001faff\u2600-\u27bf]+", re.IGNORECASE)
_EMAIL = re.compile(
    r"(?<![\w.+-])[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}(?![\w-])",
    re.IGNORECASE,
)
_PHONE = re.compile(r"(?<![\w+])(?:0|(?:\+84|0084)[ .-]?)(?:[ .-]?[0-9]){9,10}(?![\w]|[ .-]?[0-9])")
_TRAILING_URL_PUNCTUATION = ".,!?;:)]}…。，！？"


def normalize_surface(text: str) -> str:
    """Normalize spelling/case/spacing, without masking entities."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    text = unicodedata.normalize("NFC", text).lower()
    text = _TOKEN.sub(lambda match: match.group().upper(), text)
    return " ".join(text.split())


def _mask_url(match: re.Match) -> str:
    value = match.group()
    core = value.rstrip(_TRAILING_URL_PUNCTUATION)
    return "[URL]" + value[len(core):]


def _mask_phone(match: re.Match) -> str:
    value = match.group()
    digits = re.sub(r"[^0-9]", "", value)
    if value.startswith("+84"):
        digits = "0" + digits[2:]
    elif value.startswith("0084"):
        digits = "0" + digits[4:]
    mobile = len(digits) == 10 and digits[:2] in {"03", "05", "07", "08", "09"}
    landline = len(digits) == 11 and digits.startswith("02")
    return "[PHONE]" if mobile or landline else value


def normalize_text(text: str) -> str:
    """NFC + lower + whitespace + URL/email/Vietnamese phone masking.

    Other numbers, Unicode symbols, emoji and punctuation are retained.
    Existing reserved placeholders are canonical uppercase and idempotent.
    """
    text = normalize_surface(text)
    text = _URL.sub(_mask_url, text)
    text = _EMAIL.sub("[EMAIL]", text)
    text = _PHONE.sub(_mask_phone, text)
    return normalize_surface(text)
