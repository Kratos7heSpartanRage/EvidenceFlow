"""Adapter selection with one shared rate limiter per source in this process."""

from functools import lru_cache

from app.adapters.europe_pmc import EuropePMCAdapter
from app.adapters.pubmed import PubMedAdapter
from app.core.config import settings
from app.schemas.contracts import SourceName


@lru_cache(maxsize=2)
def source_adapter(source: str):
    if source == SourceName.EUROPE_PMC:
        return EuropePMCAdapter(timeout=settings.HTTP_TIMEOUT)
    if source == SourceName.PUBMED:
        return PubMedAdapter(
            email=settings.NCBI_EMAIL,
            tool=settings.NCBI_TOOL,
            api_key=settings.NCBI_API_KEY,
            timeout=settings.HTTP_TIMEOUT,
        )
    raise ValueError("Unsupported literature source")
