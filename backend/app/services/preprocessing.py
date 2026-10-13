"""Shared, non-learning text normalization for training and inference."""

import re
import unicodedata

PREPROCESSING_VERSION = "sms-nfc-whitespace-v1"
_INVISIBLE_SEPARATORS = str.maketrans({"\u200b": "", "\ufeff": ""})
_URL = re.compile(r"https?://[^\s<>\"']+|\bwww\.[^\s<>\"']+", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.IGNORECASE)
_NUMBER = re.compile(r"\d+(?:[.,:/-]\d+)*")
_TEMPLATE_TOKEN = re.compile(r"\[[a-z_]+\]|[^\W_]+", re.UNICODE)


def normalize_text(text: str) -> str:
    """Compose Vietnamese accents and collapse whitespace without masking signals.

    Preserve case, numbers, URLs, punctuation, emoji and existing placeholders.
    Raw text must be used separately for evidence offsets; normalization changes
    positions and must not be used to index the original message.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return " ".join(unicodedata.normalize("NFC", text).translate(_INVISIBLE_SEPARATORS).split())


def duplicate_key(text: str) -> str:
    """Case-insensitive normalized key for auditing, not model input."""
    return normalize_text(text).casefold()


def template_tokens(text: str) -> tuple[str, ...]:
    """Conservative split-group signature; never feed this masked view to ML.

    Mask variable URLs, emails and numbers only for identifying related templates.
    Word order is preserved in the exact signature; near matching also compares
    token sets. No Vietnamese accent removal or vocabulary fitting is performed.
    """
    signature = duplicate_key(text)
    signature = _URL.sub(" [url] ", signature)
    signature = _EMAIL.sub(" [email] ", signature)
    signature = _NUMBER.sub(" [number] ", signature)
    return tuple(_TEMPLATE_TOKEN.findall(signature))
