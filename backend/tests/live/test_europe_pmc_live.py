"""Hits the real Europe PMC API. Skipped unless EVIDENCEFLOW_LIVE=1.

Run from backend/:  EVIDENCEFLOW_LIVE=1 python -m pytest tests/live -v
Assertions are deliberately loose: live results change over time.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.adapters.europe_pmc import EuropePMCAdapter
from app.schemas.contracts import QuerySpec, SourceName

pytestmark = pytest.mark.live


def spec(**overrides) -> QuerySpec:
    values = {
        "source": SourceName.EUROPE_PMC,
        "expression": '("type 2 diabetes" OR "type II diabetes") AND metformin AND placebo',
        "date_from": date(2015, 1, 1),
        "date_to": date(2025, 12, 31),
    }
    values.update(overrides)
    return QuerySpec(**values)


def test_count_preview_and_search_agree():
    adapter = EuropePMCAdapter()
    hits = adapter.count(spec())
    assert hits > 0

    preview = adapter.preview(spec(), n=5)
    assert preview.hit_count == hits
    assert 0 < len(preview.records) <= 5
    assert all(r.title for r in preview.records)

    result = adapter.search(spec(), cap=150)  # forces more than one page if pageSize were 100
    assert result.hit_count == hits
    assert 0 < len(result.ids) <= 150
    assert result.truncated == (hits > 150)
    assert len(set(result.ids)) == len(result.ids)
    assert sum(1 for r in result.records if r.abstract) > 0


def test_synonym_flag_changes_or_keeps_hit_count():
    adapter = EuropePMCAdapter()
    plain = adapter.count(spec(expand_synonyms=False))
    expanded = adapter.count(spec(expand_synonyms=True))
    print(f"hits without synonyms={plain}, with synonyms={expanded}")
    assert expanded >= plain


def test_title_abstract_scope_narrows_results():
    adapter = EuropePMCAdapter()
    everywhere = adapter.count(spec())
    scoped = adapter.count(spec(title_abstract_only=True))
    print(f"hits anywhere incl. full text={everywhere}, titles/abstracts only={scoped}")
    assert 0 < scoped < everywhere
    preview = adapter.preview(spec(title_abstract_only=True), n=10)
    assert preview.hit_count == scoped and preview.records
    for record in preview.records:
        text = f"{record.title} {record.abstract or ''}".lower()
        assert "metformin" in text, f"{record.source_record_id} has no 'metformin' in title/abstract"


def test_known_ids_are_skipped_on_rerun():
    adapter = EuropePMCAdapter()
    first = adapter.search(spec(), cap=20)
    second = adapter.search(spec(), cap=20, known_ids=frozenset(first.ids))
    assert second.records == [] or len(second.records) < len(first.records)
    assert second.skipped_known >= len(first.ids) - 2  # tolerate small live drift


def test_nonsense_query_returns_zero_hits():
    assert EuropePMCAdapter().count(spec(expression="qwxzzyv AND plorbnatic")) == 0
