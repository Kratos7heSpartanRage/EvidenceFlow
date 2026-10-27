from app.adapters.base import RateLimiter, SourceAdapter, SourceError
from app.adapters.europe_pmc import EuropePMCAdapter
from app.adapters.pubmed import NCBI_POLICY_URL, PubMedAdapter
from app.schemas.contracts import SourceName


def get_adapter(source: SourceName | str) -> SourceAdapter:
    """Adapter for a source name, configured from environment variables."""
    source = SourceName(source)
    if source == SourceName.EUROPE_PMC:
        return EuropePMCAdapter()
    if source == SourceName.PUBMED:
        return PubMedAdapter()
    raise ValueError(f"unsupported source: {source}")


__all__ = [
    "NCBI_POLICY_URL",
    "EuropePMCAdapter",
    "PubMedAdapter",
    "RateLimiter",
    "SourceAdapter",
    "SourceError",
    "get_adapter",
]
