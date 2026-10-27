"""PubMed adapter over real HTTP against a local stub of E-utilities (no internet)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from app.adapters.base import RateLimiter, SourceError
from app.adapters.pubmed import PubMedAdapter
from app.schemas.contracts import QuerySpec, SourceName
from tests.conftest import FIXTURES

ESEARCH = (FIXTURES / "pubmed" / "esearch_page.json").read_bytes()
ESEARCH_ERROR = (FIXTURES / "pubmed" / "esearch_error.json").read_bytes()
EFETCH = (FIXTURES / "pubmed" / "efetch.xml").read_bytes()


class StubEutils(BaseHTTPRequestHandler):
    requests: list[tuple[str, dict[str, list[str]]]] = []

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        params = parse_qs(url.query)
        type(self).requests.append((url.path, params))
        if url.path.endswith("esearch.fcgi"):
            bad = "AND AND" in params.get("term", [""])[0]
            self._send(200, ESEARCH_ERROR if bad else ESEARCH, "application/json")
        elif url.path.endswith("efetch.fcgi"):
            self._send(200, EFETCH, "text/xml")
        else:
            self._send(404, json.dumps({"error": "unknown endpoint"}).encode(), "application/json")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        pass


@pytest.fixture
def stub_url(monkeypatch):
    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    StubEutils.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), StubEutils)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/entrez/eutils"
    server.shutdown()
    server.server_close()


def make_adapter(url: str) -> PubMedAdapter:
    return PubMedAdapter(
        limiter=RateLimiter(1000),
        base_url=url,
        email="team@example.org",
        api_key="",
        timeout=5,
        max_retries=1,
        sleep=lambda _s: None,
    )


def spec(expression: str = '"type 2 diabetes"[tiab] AND metformin') -> QuerySpec:
    return QuerySpec(source=SourceName.PUBMED, expression=expression)


def test_search_over_http(stub_url):
    result = make_adapter(stub_url).search(spec(), cap=100, known_ids=frozenset({"90000002"}))
    assert [r.pmid for r in result.records] == ["90000001"]
    assert result.skipped_known == 1
    (search_path, search_params), (fetch_path, fetch_params) = StubEutils.requests
    assert search_path.endswith("/esearch.fcgi") and fetch_path.endswith("/efetch.fcgi")
    assert search_params["term"] == ['"type 2 diabetes"[tiab] AND metformin']  # brackets/quotes survive
    assert fetch_params["id"] == ["90000001,90000003,90000004"]
    assert fetch_params["email"] == ["team@example.org"]


def test_esearch_error_over_http(stub_url):
    with pytest.raises(SourceError) as err:
        make_adapter(stub_url).count(spec("metformin AND AND placebo"))
    assert err.value.kind == "bad_query"
