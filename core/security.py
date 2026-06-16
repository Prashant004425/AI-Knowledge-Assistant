import os
import re
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("API_KEY", "changeme")


def verify_api_key(provided_key: str) -> bool:
    return bool(provided_key) and provided_key == API_KEY


def redact_sensitive(text: str) -> str:
    if not isinstance(text, str):
        return text

    # Redact email addresses
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[REDACTED_EMAIL]",
        text,
    )

    # Redact phone numbers (US-style and international)
    text = re.sub(
        r"\b(?:\+?\d{1,3}(?:[\s\-.])?)?(?:\(\d{2,4}\)|\d{2,4})(?:[\s\-.])?\d{3,4}(?:[\s\-.])?\d{3,4}\b",
        "[REDACTED_PHONE]",
        text,
    )

    # Redact common ID patterns
    text = re.sub(
        r"\b(?:ID|Id|id|user|uid|emp|employee)[-_]?[A-Za-z0-9]{4,}\b",
        "[REDACTED_ID]",
        text,
    )

    return text
