"""Conservative identifier and bibliographic normalization."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import unquote


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    text = unquote(unicodedata.normalize("NFKC", value)).strip().casefold()
    text = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi\s*:\s*", "", text)
    text = re.sub(r"\s+", "", text).strip("<>\"'")
    text = text.rstrip(".,;:")
    # Keep balanced parentheses that are part of real DOI suffixes.
    for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
        while text.endswith(closing) and text.count(closing) > text.count(opening):
            text = text[:-1].rstrip(".,;:")
    return text if re.fullmatch(r"10\.\d{4,9}/\S+", text) else None


def normalize_pmid(value: str | int | None) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    text = re.sub(r"^https?://pubmed\.ncbi\.nlm\.nih\.gov/", "", text, flags=re.I)
    text = re.sub(r"^pmid\s*:\s*", "", text, flags=re.I).rstrip("/ .")
    # Do not concatenate unrelated digits from malformed identifiers.
    if not re.fullmatch(r"[0-9]+", text) or int(text) == 0:
        return None
    return str(int(text))


def normalize_title(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "").casefold()
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^\w\s]|_", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def normalize_author(value: str | None) -> str:
    if not value:
        return ""
    # PubMed's usual surname + initials and 'surname, given names' forms.
    if "," in value:
        return normalize_title(value.split(",", 1)[0])
    words = value.strip().split()
    while len(words) > 1 and re.fullmatch(r"[A-Z](?:\.?[A-Z]){0,3}\.?", words[-1]):
        words.pop()
    # Preserve compound surnames after removing initials; otherwise full names
    # are intentionally compared as supplied rather than guessing their surname.
    return normalize_title(" ".join(words))


def normalize_journal(value: str | None) -> str:
    return normalize_title(value)
