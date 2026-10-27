"""Hits the real PubMed E-utilities. Skipped unless EVIDENCEFLOW_LIVE=1.

Set NCBI_EMAIL first (NCBI asks every tool to identify itself).
Windows cmd:  set EVIDENCEFLOW_LIVE=1  &  set NCBI_EMAIL=you@example.org
Then from backend/:  python -m pytest tests/live/test_pubmed_live.py -v -s
"""

from __future__ import annotations

from datetime import date

import pytest

from app.adapters.pubmed import PubMedAdapter
from app.schemas.contracts import QuerySpec, SourceName

pytestmark = pytest.mark.live


def spec(**overrides) -> QuerySpec:
    values = {
        "source": SourceName.PUBMED,
        "expression": '("type 2 diabetes" OR "type II diabetes") AND metformin AND placebo',
        "date_from": date(2015, 1, 1),
        "date_to": date(2025, 12, 31),
    }
    values.update(overrides)
    return QuerySpec(**values)


def test_count_preview_and_search():
    adapter = PubMedAdapter()
    hits = adapter.count(spec())
    print(f"PubMed hits: {hits}")
    assert hits > 0

    preview = adapter.preview(spec(), n=5)
    assert preview.hit_count == hits and 0 < len(preview.records) <= 5
    record = preview.records[0]
    assert record.pmid and record.title and record.source_record_id == record.pmid

    result = adapter.search(spec(), cap=60)
    assert 0 < len(result.ids) <= 60 and len(set(result.ids)) == len(result.ids)
    assert len(result.records) >= len(result.ids) - 3  # a few may be books or withdrawn
    assert sum(1 for r in result.records if r.abstract) > len(result.records) // 2
    assert sum(1 for r in result.records if r.doi) > 0


def test_incremental_rerun_fetches_nothing_new():
    adapter = PubMedAdapter()
    first = adapter.search(spec(), cap=20)
    second = adapter.search(spec(), cap=20, known_ids=frozenset(first.ids))
    assert second.skipped_known >= len(first.ids) - 2  # tolerate small live drift
    assert len(second.records) <= 2


def test_nonsense_query_returns_zero_hits():
    assert PubMedAdapter().count(spec(expression="qwxzzyv AND plorbnatic")) == 0
