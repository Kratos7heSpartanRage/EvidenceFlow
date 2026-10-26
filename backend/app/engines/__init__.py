"""Deterministic engines: plain data in, plain data out, no persistence or I/O."""

from .dedup import group, score_pairs
from .pico import extract_pico
from .screening import screen
from .types import CriterionSpec, PicoTerms, RecordLite

__all__ = [
    "CriterionSpec", "PicoTerms", "RecordLite", "extract_pico", "group", "score_pairs", "screen"
]
