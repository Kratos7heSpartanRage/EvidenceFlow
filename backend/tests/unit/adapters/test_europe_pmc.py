from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.adapters.base import HttpResponse, RateLimiter, SourceError, clean_text
from app.adapters.europe_pmc import EuropePMCAdapter, build_query, parse_record
from app.schemas.contracts import QuerySpec, SourceName
from tests.conftest import FakeTransport, json_response, load_fixture

PAGE1 = load_fixture("europe_pmc", "search_page1.json")
PAGE2 = load_fixture("europe_pmc", "search_page2.json")
PAGE3 = load_fixture("europe_pmc", "search_page3_end.json")
EMPTY = load_fixture("europe_pmc", "empty.json")


def spec(**overrides) -> QuerySpec:
    values = {"source": SourceName.EUROPE_PMC, "expression": "metformin AND placebo"}
    values.update(overrides)
    return QuerySpec(**values)


def adapter(transport, limiter, sleeps=None) -> EuropePMCAdapter:
    return EuropePMCAdapter(transport, limiter, max_retries=3, sleep=sleeps or (lambda _s: None))


# ------------------------------------------------------------------ query spec


class TestQuerySpecAndBuilder:
    def test_no_dates_wraps_expression(self):
        assert build_query(spec()) == "(metformin AND placebo)"

    def test_both_dates(self):
        q = build_query(spec(date_from=date(2015, 1, 1), date_to=date(2025, 12, 31)))
        assert q == "(metformin AND placebo) AND (FIRST_PDATE:[2015-01-01 TO 2025-12-31])"

    def test_open_start_and_open_end(self):
        assert "FIRST_PDATE:[1800-01-01 TO 2020-06-30]" in build_query(spec(date_to=date(2020, 6, 30)))
        assert "FIRST_PDATE:[2020-01-01 TO 2999-12-31]" in build_query(spec(date_from=date(2020, 1, 1)))

    def test_blank_expression_rejected(self):
        with pytest.raises(ValidationError):
            spec(expression="   ")

    def test_inverted_date_range_rejected(self):
        with pytest.raises(ValidationError):
            spec(date_from=date(2025, 1, 1), date_to=date(2015, 1, 1))

    def test_expression_is_trimmed(self):
        assert spec(expression="  metformin  ").expression == "metformin"


# --------------------------------------------------------------------- parsing


class TestParseRecord:
    def test_full_record(self):
        r = parse_record(PAGE1["resultList"]["result"][0])
        assert r.source == SourceName.EUROPE_PMC
        assert r.source_record_id == "MED:90000001"
        assert (r.pmid, r.pmcid, r.doi) == ("90000001", "PMC9000001", "10.1000/EXAMPLE.2020.001")
        assert r.year == 2020 and r.publication_date == "2020-03-15"
        assert r.journal == "Journal of Example Endocrinology"
        assert (r.volume, r.issue, r.pages) == ("12", "4", "101-110")
        assert r.language == "eng"
        assert [a.full_name for a in r.authors] == ["Rao A", "Kim B", "Example Diabetes Trial Group"]
        assert r.authors[0].last_name == "Rao"
        assert "Randomized Controlled Trial" in r.pub_types
        assert r.mesh_terms == ["Humans", "Metformin", "Diabetes Mellitus, Type 2"]
        assert r.keywords == ["HbA1c", "metformin"]
        assert r.raw["id"] == "90000001"

    def test_html_abstract_and_odd_shapes_are_cleaned(self):
        r = parse_record(PAGE1["resultList"]["result"][1])
        assert r.abstract == (
            "Background Male Wistar rats were fed a high-fat diet & treated with metformin. "
            "Insulin sensitivity improved."
        )
        assert r.language == "eng"  # "ENG" lowercased
        assert r.pub_types == ["Journal Article"]  # single string becomes a list
        assert r.doi is None
        assert "Animals" in r.mesh_terms
        assert [a.full_name for a in r.authors] == ["Weber D", "Lopez E"]  # from authorString

    def test_preprint_without_pmid_or_abstract(self):
        r = parse_record(PAGE1["resultList"]["result"][2])
        assert r.source_record_id == "PPR:PPR900003"
        assert r.pmid is None and r.abstract is None and r.journal is None
        assert r.year == 2021

    def test_year_falls_back_to_first_publication_date(self):
        r = parse_record(PAGE2["resultList"]["result"][2])
        assert r.year == 2018
        assert r.language == "ger"

    def test_missing_id_raises(self):
        with pytest.raises(ValueError, match="no source/id"):
            parse_record(PAGE2["resultList"]["result"][1])

    def test_missing_title_raises(self):
        with pytest.raises(ValueError, match="no title"):
            parse_record({"id": "1", "source": "MED", "title": "  "})

    def test_non_object_raises(self):
        with pytest.raises(ValueError):
            parse_record(["not", "a", "dict"])

    def test_implausible_year_ignored(self):
        r = parse_record({"id": "1", "source": "MED", "title": "T", "pubYear": "0000"})
        assert r.year is None

    def test_clean_text_handles_none_and_empty(self):
        assert clean_text(None) is None
        assert clean_text(" <b> </b> ") is None


# ---------------------------------------------------------------------- search


class TestSearch:
    def test_pages_until_cursor_stops_and_handles_bad_and_repeated_results(self, no_wait_limiter):
        t = FakeTransport(json_response(PAGE1), json_response(PAGE2), json_response(PAGE3))
        result = adapter(t, no_wait_limiter).search(spec(), cap=500)

        assert result.hit_count == 5
        assert result.ids == ["MED:90000001", "MED:90000002", "PPR:PPR900003", "MED:90000004"]
        assert [r.source_record_id for r in result.records] == result.ids
        assert result.skipped_known == 0
        assert result.truncated is False
        assert len(result.warnings) == 1 and "no source/id" in result.warnings[0]
        assert [c["params"]["cursorMark"] for c in t.calls] == ["*", "AoE1", "AoE2"]
        first = t.calls[0]["params"]
        assert first["resultType"] == "core" and first["format"] == "json"
        assert first["synonym"] == "false"
        assert first["query"] == "(metformin AND placebo)"

    def test_cap_limits_results_and_page_size(self, no_wait_limiter):
        t = FakeTransport(json_response(PAGE1))
        result = adapter(t, no_wait_limiter).search(spec(), cap=2)
        assert result.ids == ["MED:90000001", "MED:90000002"]
        assert result.truncated is True  # 5 hits > cap of 2
        assert len(t.calls) == 1 and t.calls[0]["params"]["pageSize"] == 2

    def test_known_ids_are_listed_but_not_returned(self, no_wait_limiter):
        t = FakeTransport(json_response(PAGE1), json_response(PAGE2), json_response(PAGE3))
        known = frozenset({"MED:90000001", "PPR:PPR900003"})
        result = adapter(t, no_wait_limiter).search(spec(), cap=500, known_ids=known)
        assert "MED:90000001" in result.ids
        assert [r.source_record_id for r in result.records] == ["MED:90000002", "MED:90000004"]
        assert result.skipped_known == 2

    def test_empty_results(self, no_wait_limiter):
        t = FakeTransport(json_response(EMPTY))
        result = adapter(t, no_wait_limiter).search(spec(), cap=100)
        assert result.hit_count == 0 and result.ids == [] and result.records == []
        assert result.truncated is False and len(t.calls) == 1

    def test_synonym_flag_sent_when_requested(self, no_wait_limiter):
        t = FakeTransport(json_response(EMPTY))
        adapter(t, no_wait_limiter).search(spec(expand_synonyms=True), cap=10)
        assert t.calls[0]["params"]["synonym"] == "true"

    def test_invalid_cap(self, no_wait_limiter):
        with pytest.raises(ValueError):
            adapter(FakeTransport(), no_wait_limiter).search(spec(), cap=0)


class TestPreviewAndCount:
    def test_preview_returns_hit_count_and_top_n(self, no_wait_limiter):
        t = FakeTransport(json_response(PAGE1))
        result = adapter(t, no_wait_limiter).preview(spec(), n=2)
        assert result.hit_count == 5 and len(result.records) == 2
        assert t.calls[0]["params"]["pageSize"] == 2

    def test_count_uses_cheap_request(self, no_wait_limiter):
        t = FakeTransport(json_response(EMPTY | {"hitCount": 1842}))
        assert adapter(t, no_wait_limiter).count(spec()) == 1842
        params = t.calls[0]["params"]
        assert params["pageSize"] == 1 and params["resultType"] == "lite"


# ---------------------------------------------------------------------- errors


class TestErrors:
    def test_429_is_retried_honouring_retry_after(self, no_wait_limiter, sleeps):
        t = FakeTransport(
            HttpResponse(429, b"slow down", {"Retry-After": "2"}),
            json_response(EMPTY),
        )
        result = adapter(t, no_wait_limiter, sleeps).search(spec(), cap=10)
        assert result.hit_count == 0
        assert sleeps.calls == [2.0]

    def test_5xx_retried_with_backoff_then_gives_up(self, no_wait_limiter, sleeps):
        t = FakeTransport(*[HttpResponse(503, b"down")] * 4)
        with pytest.raises(SourceError) as err:
            adapter(t, no_wait_limiter, sleeps).search(spec(), cap=10)
        assert err.value.kind == "upstream_error" and err.value.status == 503
        assert "gave up after 4 attempts" in err.value.message
        assert sleeps.calls == [0.5, 1.0, 2.0]
        assert len(t.calls) == 4

    def test_timeouts_exhausted(self, no_wait_limiter):
        t = FakeTransport(*[TimeoutError("timed out")] * 4)
        with pytest.raises(SourceError) as err:
            adapter(t, no_wait_limiter).search(spec(), cap=10)
        assert err.value.kind == "timeout"

    def test_timeout_then_success(self, no_wait_limiter):
        t = FakeTransport(TimeoutError("timed out"), json_response(EMPTY))
        assert adapter(t, no_wait_limiter).count(spec()) == 0

    def test_network_error(self, no_wait_limiter):
        t = FakeTransport(*[ConnectionError("refused")] * 4)
        with pytest.raises(SourceError) as err:
            adapter(t, no_wait_limiter).count(spec())
        assert err.value.kind == "network"

    def test_400_is_bad_query_and_not_retried(self, no_wait_limiter):
        t = FakeTransport(HttpResponse(400, b"Syntax error near AND"))
        with pytest.raises(SourceError) as err:
            adapter(t, no_wait_limiter).search(spec(), cap=10)
        assert err.value.kind == "bad_query" and "Syntax error" in err.value.message
        assert len(t.calls) == 1

    def test_invalid_json(self, no_wait_limiter):
        t = FakeTransport(HttpResponse(200, b"<html>maintenance</html>"))
        with pytest.raises(SourceError) as err:
            adapter(t, no_wait_limiter).count(spec())
        assert err.value.kind == "malformed_response"

    def test_failure_mid_paging_raises_instead_of_returning_partial(self, no_wait_limiter):
        t = FakeTransport(json_response(PAGE1), *[HttpResponse(500, b"")] * 4)
        with pytest.raises(SourceError):
            adapter(t, no_wait_limiter).search(spec(), cap=500)


# ----------------------------------------------------------------- rate limiter


def test_rate_limiter_spaces_requests():
    now = [100.0]
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    limiter = RateLimiter(4, clock=lambda: now[0], sleep=sleep)
    for _ in range(3):
        limiter.wait()
    assert slept == pytest.approx([0.25, 0.25])

    now[0] += 10  # idle time means no wait
    limiter.wait()
    assert len(slept) == 2


def test_rate_limiter_rejects_bad_rate():
    with pytest.raises(ValueError):
        RateLimiter(0)
