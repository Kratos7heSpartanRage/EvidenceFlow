"""Runs the adapter over real HTTP against a local stub server (no internet needed).

This checks the parts the unit tests fake out: URL encoding, the standard-library
transport, status-code handling and cursor paging over the wire.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from app.adapters.base import RateLimiter, SourceError
from app.adapters.europe_pmc import EuropePMCAdapter
from app.schemas.contracts import QuerySpec, SourceName
from tests.conftest import load_fixture

PAGES = {
    "*": load_fixture("europe_pmc", "search_page1.json"),
    "AoE1": load_fixture("europe_pmc", "search_page2.json"),
    "AoE2": load_fixture("europe_pmc", "search_page3_end.json"),
}


class StubEuropePMC(BaseHTTPRequestHandler):
    requests: list[dict[str, list[str]]] = []
    fail_next: list[int] = []

    def do_GET(self) -> None:  # noqa: N802
        params = parse_qs(urlparse(self.path).query)
        type(self).requests.append(params)
        if type(self).fail_next:
            self._send(type(self).fail_next.pop(0), b'{"error": "stub failure"}')
            return
        if "AND AND" in params.get("query", [""])[0]:
            self._send(400, b"Syntax error in query")
            return
        page = PAGES.get(params.get("cursorMark", ["*"])[0], PAGES["AoE2"])
        self._send(200, json.dumps(page).encode())

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        pass


@pytest.fixture
def stub_url(monkeypatch):
    # The local stub must not be routed through any configured proxy.
    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    StubEuropePMC.requests = []
    StubEuropePMC.fail_next = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), StubEuropePMC)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/europepmc/webservices/rest/search"
    server.shutdown()
    server.server_close()


def make_adapter(url: str) -> EuropePMCAdapter:
    return EuropePMCAdapter(
        limiter=RateLimiter(1000), base_url=url, timeout=5, max_retries=2, sleep=lambda _s: None
    )


def spec(expression: str = '("type 2 diabetes" OR T2DM) AND metformin') -> QuerySpec:
    return QuerySpec(source=SourceName.EUROPE_PMC, expression=expression)


def test_search_pages_over_http(stub_url):
    result = make_adapter(stub_url).search(spec(), cap=500)
    assert result.ids == ["MED:90000001", "MED:90000002", "PPR:PPR900003", "MED:90000004"]
    assert [r["cursorMark"][0] for r in StubEuropePMC.requests] == ["*", "AoE1", "AoE2"]
    # Quotes, spaces and parentheses survive URL encoding intact.
    assert StubEuropePMC.requests[0]["query"][0] == '(("type 2 diabetes" OR T2DM) AND metformin)'


def test_server_error_is_retried_over_http(stub_url):
    StubEuropePMC.fail_next = [503]
    result = make_adapter(stub_url).preview(spec(), n=3)
    assert result.hit_count == 5 and len(result.records) == 3
    assert len(StubEuropePMC.requests) == 2


def test_bad_query_maps_to_typed_error_over_http(stub_url):
    with pytest.raises(SourceError) as err:
        make_adapter(stub_url).count(spec("metformin AND AND placebo"))
    assert err.value.kind == "bad_query" and err.value.status == 400


def test_unreachable_host_is_a_network_error(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        monkeypatch.delenv(var, raising=False)
    adapter = make_adapter("http://127.0.0.1:9/nothing-listens-here")
    with pytest.raises(SourceError) as err:
        adapter.count(spec())
    assert err.value.kind == "network"
