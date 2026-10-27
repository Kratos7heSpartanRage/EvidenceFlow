from __future__ import annotations

from datetime import date

import pytest

from app.adapters.base import HttpResponse, SourceError
from app.adapters.pubmed import PubMedAdapter, parse_efetch_xml
from app.schemas.contracts import QuerySpec, SourceName
from tests.conftest import FIXTURES, FakeTransport, json_response, load_fixture

ESEARCH = load_fixture("pubmed", "esearch_page.json")
EMPTY = load_fixture("pubmed", "esearch_empty.json")
ERROR = load_fixture("pubmed", "esearch_error.json")
EFETCH = (FIXTURES / "pubmed" / "efetch.xml").read_bytes()


def xml_response(body: bytes = EFETCH) -> HttpResponse:
    return HttpResponse(200, body, {"Content-Type": "text/xml"})


def spec(**overrides) -> QuerySpec:
    values = {"source": SourceName.PUBMED, "expression": "metformin AND placebo"}
    values.update(overrides)
    return QuerySpec(**values)


def adapter(transport, limiter, **kwargs) -> PubMedAdapter:
    kwargs.setdefault("email", "team@example.org")
    kwargs.setdefault("api_key", "")
    return PubMedAdapter(transport, limiter, sleep=lambda _s: None, **kwargs)


def esearch_page(ids: list[str], count: int) -> dict:
    return {"esearchresult": {"count": str(count), "idlist": ids}}


# ---------------------------------------------------------------------- parsing


class TestParseEfetch:
    records, warnings = parse_efetch_xml(EFETCH)

    def by_pmid(self, pmid):
        return next(r for r in self.records if r.pmid == pmid)

    def test_only_usable_articles_become_records(self):
        assert [r.source_record_id for r in self.records] == ["90000001", "90000002"]
        assert any("90000003" in w and "no title" in w for w in self.warnings)
        assert any("book record" in w for w in self.warnings)

    def test_full_article(self):
        r = self.by_pmid("90000001")
        assert r.source == SourceName.PUBMED
        assert (
            r.title == "Effect of metformin versus placebo on HbA1c in adults with type 2 diabetes."
        )
        assert r.abstract.startswith("BACKGROUND: Metformin is first-line therapy. METHODS: Adults")
        assert "RESULTS: The primary outcome was change in HbA1c." in r.abstract
        assert r.doi == "10.1000/EXAMPLE.2020.001"  # ArticleIdList preferred over ELocationID
        assert r.pmcid == "PMC9000001"
        assert [a.full_name for a in r.authors] == [
            "Rao A",
            "Kim B",
            "Example Diabetes Trial Group",
        ]
        assert r.authors[0].last_name == "Rao" and r.authors[2].last_name is None
        assert (r.year, r.publication_date) == (2020, "2020-02-28")  # electronic date preferred
        assert (r.journal, r.volume, r.issue, r.pages) == (
            "Journal of Example Endocrinology",
            "12",
            "4",
            "101-110",
        )
        assert r.language == "eng"
        assert r.pub_types == ["Randomized Controlled Trial", "Journal Article"]
        assert r.mesh_terms == ["Humans", "Metformin"]
        assert r.keywords == ["HbA1c"]
        assert r.raw["format"] == "pubmed_xml" and "<PMID" in r.raw["xml"]

    def test_medline_date_elocation_doi_and_missing_abstract(self):
        r = self.by_pmid("90000002")
        assert r.year == 2019 and r.publication_date is None
        assert r.doi == "10.1000/beispiel.2019.002"
        assert r.abstract is None
        assert r.language == "ger"
        assert r.pmcid is None

    def test_invalid_xml(self):
        with pytest.raises(SourceError) as err:
            parse_efetch_xml(b"<html>maintenance")
        assert err.value.kind == "malformed_response"


# ---------------------------------------------------------------------- search


class TestSearch:
    def test_esearch_then_efetch_with_required_ncbi_params(self, no_wait_limiter):
        t = FakeTransport(json_response(ESEARCH), xml_response())
        result = adapter(t, no_wait_limiter).search(spec(), cap=500)

        assert result.hit_count == 4
        assert result.ids == ["90000001", "90000002", "90000003", "90000004"]
        assert [r.pmid for r in result.records] == ["90000001", "90000002"]
        assert result.truncated is False
        assert any("90000003, 90000004" in w for w in result.warnings)

        esearch, efetch = t.calls
        assert esearch["url"].endswith("/esearch.fcgi") and efetch["url"].endswith("/efetch.fcgi")
        assert esearch["params"]["term"] == "metformin AND placebo"
        assert esearch["params"]["retmode"] == "json" and esearch["params"]["retmax"] == 500
        for call in t.calls:
            assert call["params"]["tool"] == "evidenceflow"
            assert call["params"]["email"] == "team@example.org"
            assert "api_key" not in call["params"]
        assert efetch["params"]["id"] == "90000001,90000002,90000003,90000004"
        assert efetch["params"]["retmode"] == "xml"

    def test_incremental_fetch_downloads_only_unknown_pmids(self, no_wait_limiter):
        t = FakeTransport(json_response(ESEARCH), xml_response())
        known = frozenset({"90000001", "90000004"})
        result = adapter(t, no_wait_limiter).search(spec(), cap=500, known_ids=known)
        assert t.calls[1]["params"]["id"] == "90000002,90000003"
        assert result.skipped_known == 2
        assert len(result.ids) == 4

    def test_everything_known_means_no_efetch(self, no_wait_limiter):
        t = FakeTransport(json_response(ESEARCH))
        result = adapter(t, no_wait_limiter).search(
            spec(), cap=500, known_ids=frozenset(ESEARCH["esearchresult"]["idlist"])
        )
        assert result.records == [] and result.skipped_known == 4 and len(t.calls) == 1

    def test_date_range_uses_publication_date(self, no_wait_limiter):
        t = FakeTransport(json_response(EMPTY))
        adapter(t, no_wait_limiter).search(
            spec(date_from=date(2015, 1, 1), date_to=date(2025, 12, 31)), cap=10
        )
        params = t.calls[0]["params"]
        assert (params["datetype"], params["mindate"], params["maxdate"]) == (
            "pdat",
            "2015/01/01",
            "2025/12/31",
        )

    def test_open_ended_date(self, no_wait_limiter):
        t = FakeTransport(json_response(EMPTY))
        adapter(t, no_wait_limiter).count(spec(date_from=date(2020, 1, 1)))
        assert (t.calls[0]["params"]["mindate"], t.calls[0]["params"]["maxdate"]) == (
            "2020/01/01",
            "3000/12/31",
        )

    def test_title_abstract_flag_does_not_change_pubmed_term(self, no_wait_limiter):
        t = FakeTransport(json_response(EMPTY))
        adapter(t, no_wait_limiter).count(spec(title_abstract_only=True))
        assert t.calls[0]["params"]["term"] == "metformin AND placebo"

    def test_no_dates_sends_no_date_params(self, no_wait_limiter):
        t = FakeTransport(json_response(EMPTY))
        adapter(t, no_wait_limiter).count(spec())
        assert "mindate" not in t.calls[0]["params"]

    def test_cap_and_truncation(self, no_wait_limiter):
        t = FakeTransport(
            json_response(esearch_page(["1", "2"], count=13790)),
            xml_response(b"<PubmedArticleSet/>"),
        )
        result = adapter(t, no_wait_limiter).search(spec(), cap=2)
        assert result.ids == ["1", "2"] and result.truncated is True
        assert t.calls[0]["params"]["retmax"] == 2

    def test_pages_esearch_when_a_page_comes_back_short(self, no_wait_limiter):
        t = FakeTransport(
            json_response(esearch_page(["1", "2"], count=3)),
            json_response(
                esearch_page(["2", "3"], count=3)
            ),  # overlapping page: repeated id ignored
            xml_response(b"<PubmedArticleSet/>"),
        )
        result = adapter(t, no_wait_limiter).search(spec(), cap=10)
        assert result.ids == ["1", "2", "3"]
        assert t.calls[1]["params"]["retstart"] == 2

    def test_efetch_is_batched(self, no_wait_limiter):
        ids = [str(i) for i in range(1, 451)]
        empty = xml_response(b"<PubmedArticleSet/>")
        t = FakeTransport(json_response(esearch_page(ids, count=450)), empty, empty, empty)
        adapter(t, no_wait_limiter).search(spec(), cap=500)
        sizes = [len(c["params"]["id"].split(",")) for c in t.calls[1:]]
        assert sizes == [200, 200, 50]

    def test_empty_results(self, no_wait_limiter):
        t = FakeTransport(json_response(EMPTY))
        result = adapter(t, no_wait_limiter).search(spec(), cap=100)
        assert (result.hit_count, result.ids, result.records) == (0, [], [])
        assert len(t.calls) == 1

    def test_esearch_error_is_bad_query(self, no_wait_limiter):
        t = FakeTransport(json_response(ERROR))
        with pytest.raises(SourceError) as err:
            adapter(t, no_wait_limiter).search(spec(), cap=10)
        assert err.value.kind == "bad_query" and "AND AND" in err.value.message


class TestPreviewCountAndConfig:
    def test_count_requests_no_ids(self, no_wait_limiter):
        t = FakeTransport(json_response(esearch_page([], count=13790)))
        assert adapter(t, no_wait_limiter).count(spec()) == 13790
        assert t.calls[0]["params"]["retmax"] == 0

    def test_preview(self, no_wait_limiter):
        t = FakeTransport(json_response(ESEARCH), xml_response())
        result = adapter(t, no_wait_limiter).preview(spec(), n=4)
        assert result.hit_count == 4 and len(result.records) == 2
        assert t.calls[0]["params"]["retmax"] == 4

    def test_api_key_sent_and_raises_rate_limit(self):
        t = FakeTransport(json_response(EMPTY))
        a = PubMedAdapter(t, email="x@example.org", api_key="secret", sleep=lambda _s: None)
        a.count(spec())
        assert t.calls[0]["params"]["api_key"] == "secret"
        assert a.limiter.min_interval < 1 / 3

    def test_default_rate_stays_under_three_per_second(self):
        a = PubMedAdapter(FakeTransport(), email="x@example.org", api_key="")
        assert a.limiter.min_interval > 1 / 3

    def test_settings_come_from_environment(self, monkeypatch):
        monkeypatch.setenv("NCBI_EMAIL", "env@example.org")
        monkeypatch.setenv("NCBI_TOOL", "evidenceflow-test")
        monkeypatch.delenv("NCBI_API_KEY", raising=False)
        t = FakeTransport(json_response(EMPTY))
        PubMedAdapter(t, sleep=lambda _s: None).count(spec())
        assert t.calls[0]["params"]["email"] == "env@example.org"
        assert t.calls[0]["params"]["tool"] == "evidenceflow-test"

    def test_retries_on_429(self, no_wait_limiter, sleeps):
        t = FakeTransport(HttpResponse(429, b"", {"Retry-After": "1"}), json_response(EMPTY))
        assert (
            PubMedAdapter(t, no_wait_limiter, email="x@e.org", api_key="", sleep=sleeps).count(
                spec()
            )
            == 0
        )
        assert sleeps.calls == [1.0]

    def test_efetch_failure_raises(self, no_wait_limiter):
        t = FakeTransport(json_response(ESEARCH), *[HttpResponse(502, b"")] * 4)
        with pytest.raises(SourceError) as err:
            adapter(t, no_wait_limiter).search(spec(), cap=10)
        assert err.value.kind == "upstream_error"
