"""PubMed adapter using NCBI E-utilities (ESearch for IDs, EFetch for records).

API: https://www.ncbi.nlm.nih.gov/books/NBK25501/

NCBI rules this adapter follows:
- At most 3 requests/second without an API key, 10 with one (NCBI_API_KEY).
- Every request carries `tool` and `email` so NCBI can contact the developer.
  Set NCBI_EMAIL (and optionally NCBI_TOOL, NCBI_API_KEY) in the environment.
- Large jobs belong on weekends or 9 pm - 5 am US Eastern; the import cap keeps
  ordinary searches small.
- Any UI showing PubMed content must display NCBI's disclaimer; see
  NCBI_POLICY_URL.

Incremental fetch: ESearch returns only PMIDs. EFetch is called only for PMIDs
that are not already stored, so re-running a search downloads nothing it has.
"""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET  # noqa: S405 (trusted NCBI source)
from collections.abc import Callable, Iterable
from typing import Any

from app.adapters.base import (
    HttpTransport,
    RateLimiter,
    SourceError,
    UrllibTransport,
    clean_id,
    clean_text,
    request_bytes,
    request_json,
)
from app.schemas.contracts import Author, PreviewResult, QuerySpec, RecordIn, SearchResult, SourceName

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_POLICY_URL = "https://www.ncbi.nlm.nih.gov/home/about/policies/"
DEFAULT_TOOL = "evidenceflow"
ESEARCH_MAX_PAGE = 10_000  # PubMed ESearch also stops at the first 10,000 results
EFETCH_BATCH = 200
OPEN_START = "1800/01/01"
OPEN_END = "3000/12/31"

_MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
    )
}


class PubMedAdapter:
    name = SourceName.PUBMED.value

    def __init__(
        self,
        transport: HttpTransport | None = None,
        limiter: RateLimiter | None = None,
        *,
        email: str | None = None,
        tool: str | None = None,
        api_key: str | None = None,
        base_url: str = EUTILS_BASE,
        timeout: float = 30.0,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.email = email if email is not None else os.environ.get("NCBI_EMAIL") or None
        self.tool = tool or os.environ.get("NCBI_TOOL") or DEFAULT_TOOL
        self.api_key = api_key if api_key is not None else os.environ.get("NCBI_API_KEY") or None
        self.transport = transport or UrllibTransport()
        # Stay just under NCBI's published limits.
        self.limiter = limiter or RateLimiter(9.0 if self.api_key else 2.8)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._sleep = sleep

    # ------------------------------------------------------------------ public

    def count(self, spec: QuerySpec) -> int:
        count, _ids = self._esearch(spec, retstart=0, retmax=0)
        return count

    def preview(self, spec: QuerySpec, n: int = 20) -> PreviewResult:
        n = max(1, min(n, ESEARCH_MAX_PAGE))
        count, ids = self._esearch(spec, retstart=0, retmax=n)
        records, warnings = self._efetch(ids)
        return PreviewResult(hit_count=count, records=records, warnings=warnings)

    def search(self, spec: QuerySpec, cap: int, known_ids: frozenset[str] = frozenset()) -> SearchResult:
        if cap < 1:
            raise ValueError("cap must be at least 1")
        cap = min(cap, ESEARCH_MAX_PAGE)
        ids: list[str] = []
        seen: set[str] = set()
        hit_count: int | None = None
        while len(ids) < cap:
            count, page = self._esearch(spec, retstart=len(ids), retmax=min(ESEARCH_MAX_PAGE, cap - len(ids)))
            if hit_count is None:
                hit_count = count
            new_on_page = [pmid for pmid in page if pmid not in seen]
            for pmid in new_on_page[: cap - len(ids)]:
                seen.add(pmid)
                ids.append(pmid)
            if not new_on_page or len(ids) >= count:
                break

        to_fetch = [pmid for pmid in ids if pmid not in known_ids]
        records, warnings = self._efetch(to_fetch)
        hit_count = hit_count or 0
        return SearchResult(
            hit_count=hit_count,
            ids=ids,
            records=records,
            skipped_known=len(ids) - len(to_fetch),
            truncated=hit_count > cap,
            warnings=warnings,
        )

    # ----------------------------------------------------------------- private

    def _common_params(self) -> dict[str, str]:
        params = {"tool": self.tool}
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _request_kwargs(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "transport": self.transport,
            "limiter": self.limiter,
            "source": self.name,
            "url": f"{self.base_url}/{endpoint}",
            "params": params,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "sleep": self._sleep,
        }

    def _esearch(self, spec: QuerySpec, *, retstart: int, retmax: int) -> tuple[int, list[str]]:
        params: dict[str, Any] = {
            "db": "pubmed",
            "term": spec.expression,
            "retmode": "json",
            "retstart": retstart,
            "retmax": retmax,
            **self._common_params(),
        }
        if spec.date_from or spec.date_to:
            params["datetype"] = "pdat"
            params["mindate"] = spec.date_from.strftime("%Y/%m/%d") if spec.date_from else OPEN_START
            params["maxdate"] = spec.date_to.strftime("%Y/%m/%d") if spec.date_to else OPEN_END

        data = request_json(**self._request_kwargs("esearch.fcgi", params))
        result = data.get("esearchresult") if isinstance(data, dict) else None
        if not isinstance(result, dict):
            raise SourceError("malformed_response", self.name, "ESearch response has no esearchresult")
        if result.get("ERROR"):
            raise SourceError("bad_query", self.name, f"PubMed rejected the query: {result['ERROR']}", 200)
        try:
            count = max(int(result.get("count", 0)), 0)
        except (TypeError, ValueError):
            count = 0
        ids = [pmid for pmid in (clean_id(x) for x in result.get("idlist") or []) if pmid]
        return count, ids

    def _efetch(self, pmids: list[str]) -> tuple[list[RecordIn], list[str]]:
        by_pmid: dict[str, RecordIn] = {}
        warnings: list[str] = []
        for batch in _chunks(pmids, EFETCH_BATCH):
            params = {"db": "pubmed", "id": ",".join(batch), "retmode": "xml", **self._common_params()}
            body = request_bytes(**self._request_kwargs("efetch.fcgi", params))
            records, batch_warnings = parse_efetch_xml(body)
            warnings.extend(batch_warnings)
            for record in records:
                by_pmid[record.source_record_id] = record
            missing = [pmid for pmid in batch if pmid not in by_pmid]
            if missing:
                warnings.append(f"PubMed returned no record for PMID(s) {', '.join(missing[:10])}")
        # Keep search rank order.
        return [by_pmid[pmid] for pmid in pmids if pmid in by_pmid], warnings


# ---------------------------------------------------------------------- parsing


def parse_efetch_xml(body: bytes) -> tuple[list[RecordIn], list[str]]:
    """Parse an EFetch PubmedArticleSet. Unusable articles become warnings."""
    try:
        root = ET.fromstring(body)  # noqa: S314 (trusted NCBI source)
    except ET.ParseError as exc:
        raise SourceError("malformed_response", SourceName.PUBMED.value, f"invalid XML: {exc}", 200) from exc
    records: list[RecordIn] = []
    warnings: list[str] = []
    for article in root.findall("PubmedArticle"):
        try:
            records.append(parse_article(article))
        except ValueError as exc:
            warnings.append(str(exc))
    books = len(root.findall("PubmedBookArticle"))
    if books:
        warnings.append(f"skipped {books} book record(s); only journal articles are imported")
    return records, warnings


def parse_article(article: ET.Element) -> RecordIn:
    citation = article.find("MedlineCitation")
    if citation is None:
        raise ValueError("skipped an article with no MedlineCitation")
    pmid = clean_id(_text(citation.find("PMID")))
    if not pmid:
        raise ValueError("skipped an article with no PMID")
    art = citation.find("Article")
    if art is None:
        raise ValueError(f"skipped PMID {pmid}: no Article element")
    title = _text(art.find("ArticleTitle")) or _text(art.find("VernacularTitle"))
    if not title:
        raise ValueError(f"skipped PMID {pmid}: no title")

    journal = art.find("Journal")
    issue = journal.find("JournalIssue") if journal is not None else None
    pub_date = issue.find("PubDate") if issue is not None else None

    ids = {
        (el.get("IdType") or "").lower(): clean_id(el.text)
        for el in article.findall("PubmedData/ArticleIdList/ArticleId")
    }
    doi = ids.get("doi") or next(
        (
            clean_id(el.text)
            for el in art.findall("ELocationID")
            if (el.get("EIdType") or "").lower() == "doi"
        ),
        None,
    )
    languages = [lang for lang in (clean_id(el.text) for el in art.findall("Language")) if lang]

    return RecordIn(
        source=SourceName.PUBMED,
        source_record_id=pmid,
        doi=doi,
        pmid=pmid,
        pmcid=ids.get("pmc"),
        title=title,
        abstract=_abstract(art),
        authors=_authors(art),
        year=_year(pub_date, art),
        publication_date=_iso_date(art.find("ArticleDate")) or _iso_date(pub_date),
        journal=_text(journal.find("Title")) if journal is not None else None,
        volume=_text(issue.find("Volume")) if issue is not None else None,
        issue=_text(issue.find("Issue")) if issue is not None else None,
        pages=_text(art.find("Pagination/MedlinePgn")),
        language=languages[0].lower() if languages else None,
        pub_types=_texts(art.findall("PublicationTypeList/PublicationType")),
        mesh_terms=_texts(citation.findall("MeshHeadingList/MeshHeading/DescriptorName")),
        keywords=_texts(citation.findall("KeywordList/Keyword")),
        raw={"format": "pubmed_xml", "xml": ET.tostring(article, encoding="unicode")},
    )


def _text(element: ET.Element | None) -> str | None:
    """All text inside an element, including inline markup like <i> or <sup>."""
    if element is None:
        return None
    return clean_text("".join(element.itertext()))


def _texts(elements: Iterable[ET.Element]) -> list[str]:
    return [t for t in (_text(el) for el in elements) if t]


def _abstract(art: ET.Element) -> str | None:
    parts = []
    for section in art.findall("Abstract/AbstractText"):
        text = _text(section)
        if not text:
            continue
        label = (section.get("Label") or "").strip()
        parts.append(f"{label}: {text}" if label else text)
    return " ".join(parts) or None


def _authors(art: ET.Element) -> list[Author]:
    authors = []
    for author in art.findall("AuthorList/Author"):
        collective = _text(author.find("CollectiveName"))
        last = _text(author.find("LastName"))
        initials = _text(author.find("Initials"))
        if last:
            authors.append(
                Author(
                    full_name=f"{last} {initials}".strip() if initials else last,
                    last_name=last,
                    initials=initials,
                )
            )
        elif collective:
            authors.append(Author(full_name=collective))
    return authors


def _year(pub_date: ET.Element | None, art: ET.Element) -> int | None:
    candidates = []
    if pub_date is not None:
        candidates.append(_text(pub_date.find("Year")))
        candidates.append((_text(pub_date.find("MedlineDate")) or "")[:4])  # e.g. "2019 Jan-Feb"
    candidates.append(_text(art.find("ArticleDate/Year")))
    for value in candidates:
        if value and value.isdigit() and 1500 <= int(value) <= 2999:
            return int(value)
    return None


def _iso_date(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    year = _text(element.find("Year"))
    if not year or not year.isdigit():
        return None
    month_text = (_text(element.find("Month")) or "").lower()
    month = int(month_text) if month_text.isdigit() else _MONTHS.get(month_text[:3])
    day_text = _text(element.find("Day")) or ""
    if not month:
        return None
    day = int(day_text) if day_text.isdigit() else 1
    return f"{int(year):04d}-{month:02d}-{day:02d}"


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
