"""Europe PMC REST adapter.

API: https://europepmc.org/RestfulWebService (search endpoint, JSON, cursor paging).
No API key or registration is needed.

Behaviour worth knowing:
- MeSH synonym expansion: we always send `synonym` explicitly from
  QuerySpec.expand_synonyms, so hit counts never depend on the API default.
- QuerySpec.title_abstract_only scopes the expression with TITLE_ABS:(...), so
  terms must appear in the title or abstract rather than anywhere in the full
  text. Expressions that already use their own field prefixes (e.g. AUTH:)
  should leave this off.
- Date range is applied as FIRST_PDATE:[from TO to] (first publication date).
  An open end uses a far-past or far-future bound.
- Europe PMC returns full records in search pages, so "incremental" here means
  records already in the database are skipped (listed in `ids`, not re-returned
  in `records`). The pages themselves are still downloaded.
- source_record_id is "<SRC>:<id>", e.g. "MED:31415926", because Europe PMC
  ids are only unique within a source (MED, PMC, PPR, AGR, ...).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app.adapters.base import (
    HttpTransport,
    RateLimiter,
    SourceError,
    UrllibTransport,
    clean_id,
    clean_text,
    request_json,
)
from app.schemas.contracts import Author, PreviewResult, QuerySpec, RecordIn, SearchResult, SourceName

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
MAX_PAGE_SIZE = 1000
DEFAULT_REQUESTS_PER_SECOND = 5.0
OPEN_START = "1800-01-01"
OPEN_END = "2999-12-31"


def build_query(spec: QuerySpec) -> str:
    """Combine the researcher's expression with the scope and date filters."""
    query = f"({spec.expression})"
    if spec.title_abstract_only:
        # Field-scope the whole Boolean expression; a field prefix applies to
        # every term inside the parentheses.
        query = f"TITLE_ABS:{query}"
    if spec.date_from or spec.date_to:
        start = spec.date_from.isoformat() if spec.date_from else OPEN_START
        end = spec.date_to.isoformat() if spec.date_to else OPEN_END
        query += f" AND (FIRST_PDATE:[{start} TO {end}])"
    return query


class EuropePMCAdapter:
    name = SourceName.EUROPE_PMC.value

    def __init__(
        self,
        transport: HttpTransport | None = None,
        limiter: RateLimiter | None = None,
        *,
        base_url: str = BASE_URL,
        timeout: float = 20.0,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.transport = transport or UrllibTransport()
        self.limiter = limiter or RateLimiter(DEFAULT_REQUESTS_PER_SECOND)
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._sleep = sleep

    # ------------------------------------------------------------------ public

    def count(self, spec: QuerySpec) -> int:
        data = self._get(spec, page_size=1, cursor="*", result_type="lite")
        return _hit_count(data)

    def preview(self, spec: QuerySpec, n: int = 20) -> PreviewResult:
        n = max(1, min(n, MAX_PAGE_SIZE))
        data = self._get(spec, page_size=n, cursor="*", result_type="core")
        records, warnings = [], []
        for item in _results(data)[:n]:
            try:
                records.append(parse_record(item))
            except ValueError as exc:
                warnings.append(str(exc))
        return PreviewResult(hit_count=_hit_count(data), records=records, warnings=warnings)

    def search(self, spec: QuerySpec, cap: int, known_ids: frozenset[str] = frozenset()) -> SearchResult:
        if cap < 1:
            raise ValueError("cap must be at least 1")
        ids: list[str] = []
        seen: set[str] = set()
        records: list[RecordIn] = []
        warnings: list[str] = []
        skipped_known = 0
        hit_count: int | None = None
        cursor = "*"

        while len(ids) < cap:
            page_size = min(MAX_PAGE_SIZE, cap - len(ids))
            data = self._get(spec, page_size=page_size, cursor=cursor, result_type="core")
            if hit_count is None:
                hit_count = _hit_count(data)
            page = _results(data)
            for item in page:
                if len(ids) >= cap:
                    break
                try:
                    record = parse_record(item)
                except ValueError as exc:
                    warnings.append(str(exc))
                    continue
                if record.source_record_id in seen:
                    continue  # the source repeated a record across pages
                seen.add(record.source_record_id)
                ids.append(record.source_record_id)
                if record.source_record_id in known_ids:
                    skipped_known += 1
                else:
                    records.append(record)
            next_cursor = data.get("nextCursorMark")
            if not page or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

        hit_count = hit_count or 0
        return SearchResult(
            hit_count=hit_count,
            ids=ids,
            records=records,
            skipped_known=skipped_known,
            truncated=hit_count > cap,
            warnings=warnings,
        )

    # ----------------------------------------------------------------- private

    def _get(self, spec: QuerySpec, *, page_size: int, cursor: str, result_type: str) -> dict[str, Any]:
        params = {
            "query": build_query(spec),
            "format": "json",
            "resultType": result_type,
            "pageSize": page_size,
            "cursorMark": cursor,
            "synonym": "true" if spec.expand_synonyms else "false",
        }
        data = request_json(
            transport=self.transport,
            limiter=self.limiter,
            source=self.name,
            url=self.base_url,
            params=params,
            timeout=self.timeout,
            max_retries=self.max_retries,
            sleep=self._sleep,
        )
        if not isinstance(data, dict):
            raise SourceError("malformed_response", self.name, "expected a JSON object")
        return data


# ---------------------------------------------------------------------- parsing


def parse_record(item: Any) -> RecordIn:
    """Map one Europe PMC result to RecordIn. Raises ValueError if unusable."""
    if not isinstance(item, dict):
        raise ValueError("skipped a result that is not an object")
    src = clean_id(item.get("source"))
    rid = clean_id(item.get("id"))
    if not src or not rid:
        raise ValueError(f"skipped a result with no source/id (title: {clean_text(item.get('title'))!r})")
    title = clean_text(item.get("title"))
    if not title:
        raise ValueError(f"skipped {src}:{rid}: no title")

    journal_info = item.get("journalInfo") if isinstance(item.get("journalInfo"), dict) else {}
    journal = journal_info.get("journal") if isinstance(journal_info.get("journal"), dict) else {}

    return RecordIn(
        source=SourceName.EUROPE_PMC,
        source_record_id=f"{src}:{rid}",
        doi=clean_id(item.get("doi")),
        pmid=clean_id(item.get("pmid")),
        pmcid=clean_id(item.get("pmcid")),
        title=title,
        abstract=clean_text(item.get("abstractText")),
        authors=_authors(item),
        year=_year(item, journal_info),
        publication_date=clean_id(item.get("firstPublicationDate")),
        journal=clean_text(journal.get("title")) or clean_text(item.get("journalTitle")),
        volume=clean_id(journal_info.get("volume")),
        issue=clean_id(journal_info.get("issue")),
        pages=clean_id(item.get("pageInfo")),
        language=(clean_id(item.get("language")) or "").lower() or None,
        pub_types=_texts(_nested(item, "pubTypeList", "pubType")),
        mesh_terms=_mesh(item),
        keywords=_texts(_nested(item, "keywordList", "keyword")),
        raw=item,
    )


def _authors(item: dict[str, Any]) -> list[Author]:
    authors: list[Author] = []
    for entry in _as_list(_nested(item, "authorList", "author")):
        if not isinstance(entry, dict):
            continue
        full = clean_text(entry.get("fullName")) or clean_text(entry.get("collectiveName"))
        last = clean_text(entry.get("lastName"))
        initials = clean_text(entry.get("initials"))
        if not full and last:
            full = f"{last} {initials}".strip() if initials else last
        if full:
            authors.append(Author(full_name=full, last_name=last, initials=initials))
    if authors:
        return authors
    # Lite results only have "Smith J, Doe A." in authorString.
    author_string = clean_text(item.get("authorString"))
    if not author_string:
        return []
    for name in author_string.rstrip(".").split(","):
        name = name.strip()
        if name:
            parts = name.split()
            authors.append(Author(full_name=name, last_name=parts[0] if len(parts) > 1 else None))
    return authors


def _year(item: dict[str, Any], journal_info: dict[str, Any]) -> int | None:
    candidates = [
        item.get("pubYear"),
        journal_info.get("yearOfPublication"),
        (item.get("firstPublicationDate") or "")[:4],
    ]
    for value in candidates:
        try:
            year = int(str(value).strip())
        except (TypeError, ValueError):
            continue
        if 1500 <= year <= 2999:
            return year
    return None


def _mesh(item: dict[str, Any]) -> list[str]:
    terms = []
    for heading in _as_list(_nested(item, "meshHeadingList", "meshHeading")):
        name = clean_text(heading.get("descriptorName")) if isinstance(heading, dict) else clean_text(heading)
        if name:
            terms.append(name)
    return terms


def _nested(item: dict[str, Any], outer: str, inner: str) -> Any:
    container = item.get(outer)
    return container.get(inner) if isinstance(container, dict) else None


def _texts(value: Any) -> list[str]:
    return [t for t in (clean_text(x) for x in _as_list(value)) if t]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _results(data: dict[str, Any]) -> list[Any]:
    result_list = data.get("resultList")
    results = result_list.get("result") if isinstance(result_list, dict) else None
    return results if isinstance(results, list) else []


def _hit_count(data: dict[str, Any]) -> int:
    try:
        return max(int(data.get("hitCount", 0)), 0)
    except (TypeError, ValueError):
        return 0
