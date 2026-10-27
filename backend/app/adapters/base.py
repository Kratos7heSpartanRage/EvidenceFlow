"""Shared plumbing for literature-source adapters.

Uses only the standard library for HTTP so adapters run anywhere without extra
dependencies. Every outbound request goes through `request_bytes`, which applies
the per-source rate limit, a timeout, retries with backoff on 429/5xx/timeouts,
and maps failures to a typed `SourceError`.
"""

from __future__ import annotations

import html
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.schemas.contracts import PreviewResult, QuerySpec, SearchResult

USER_AGENT = "EvidenceFlow/0.1 (systematic review hackathon tool)"

ErrorKind = Literal[
    "timeout",
    "rate_limited",
    "bad_query",
    "upstream_error",
    "network",
    "malformed_response",
]


class SourceError(Exception):
    """A literature source could not answer. Safe to show to the reviewer."""

    def __init__(self, kind: ErrorKind, source: str, message: str, status: int | None = None):
        super().__init__(f"[{source}] {kind}: {message}")
        self.kind = kind
        self.source = source
        self.message = message
        self.status = status


# --------------------------------------------------------------------------- HTTP


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)


class HttpTransport(Protocol):
    """Performs one GET. Raises TimeoutError or ConnectionError on network failure."""

    def get(self, url: str, params: Mapping[str, Any], timeout: float) -> HttpResponse: ...


class UrllibTransport:
    """Default transport. Honours HTTPS_PROXY and friends from the environment."""

    def get(self, url: str, params: Mapping[str, Any], timeout: float) -> HttpResponse:
        full_url = f"{url}?{urllib.parse.urlencode(params)}" if params else url
        request = urllib.request.Request(  # noqa: S310 (fixed https hosts)
            full_url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return HttpResponse(response.status, response.read(), dict(response.headers))
        except urllib.error.HTTPError as exc:
            return HttpResponse(exc.code, exc.read() or b"", dict(exc.headers or {}))
        except TimeoutError as exc:
            raise TimeoutError(str(exc)) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TimeoutError(str(exc.reason)) from exc
            raise ConnectionError(str(exc.reason)) from exc


class RateLimiter:
    """Spaces requests at least 1/rate seconds apart. Thread-safe."""

    def __init__(
        self,
        requests_per_second: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self.min_interval = 1.0 / requests_per_second
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            delay = self._next_allowed - now
            if delay > 0:
                self._sleep(delay)
                now += delay
            self._next_allowed = now + self.min_interval


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRY_AFTER_SECONDS = 30.0


def request_json(**kwargs: Any) -> Any:
    """GET a JSON document. Same arguments and behaviour as `request_bytes`."""
    source = kwargs["source"]
    body = request_bytes(**kwargs)
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceError("malformed_response", source, f"invalid JSON: {exc}", 200) from exc


def request_bytes(
    *,
    transport: HttpTransport,
    limiter: RateLimiter,
    source: str,
    url: str,
    params: Mapping[str, Any],
    timeout: float = 20.0,
    max_retries: int = 3,
    backoff_base: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> bytes:
    """GET a document with rate limiting, retries and typed errors."""
    last_error: SourceError | None = None
    for attempt in range(max_retries + 1):
        if attempt > 0:
            retry_after = _retry_after_seconds(last_error)
            sleep(retry_after if retry_after is not None else backoff_base * (2 ** (attempt - 1)))
        limiter.wait()
        try:
            response = transport.get(url, params, timeout)
        except TimeoutError as exc:
            last_error = SourceError("timeout", source, f"no response within {timeout:.0f}s ({exc})")
            continue
        except (ConnectionError, OSError) as exc:
            last_error = SourceError("network", source, f"could not reach the source ({exc})")
            continue

        if response.status == 200:
            return response.body

        detail = _short_body(response.body)
        if response.status in RETRYABLE_STATUS:
            kind: ErrorKind = "rate_limited" if response.status == 429 else "upstream_error"
            last_error = SourceError(kind, source, f"HTTP {response.status} {detail}", response.status)
            last_error.retry_after = response.headers.get("Retry-After")  # type: ignore[attr-defined]
            continue
        if response.status == 400:
            raise SourceError("bad_query", source, f"the source rejected the query: {detail}", 400)
        raise SourceError("upstream_error", source, f"HTTP {response.status} {detail}", response.status)

    assert last_error is not None
    last_error.message = f"{last_error.message} (gave up after {max_retries + 1} attempts)"
    raise last_error


def _retry_after_seconds(error: SourceError | None) -> float | None:
    value = getattr(error, "retry_after", None)
    if value is None:
        return None
    try:
        return min(max(float(value), 0.0), MAX_RETRY_AFTER_SECONDS)
    except (TypeError, ValueError):
        return None


def _short_body(body: bytes, limit: int = 200) -> str:
    text = body.decode("utf-8", errors="replace").strip()
    return text[:limit]


# --------------------------------------------------------------------------- text

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def clean_text(value: Any) -> str | None:
    """Strip HTML tags and entities, collapse whitespace. Empty becomes None."""
    if value is None:
        return None
    text = str(value)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text or None


def clean_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# --------------------------------------------------------------------------- interface


class SourceAdapter(Protocol):
    """What every literature source provides. Adapters never touch the database."""

    name: str

    def count(self, spec: QuerySpec) -> int:
        """Hit count only (cheap)."""
        ...

    def preview(self, spec: QuerySpec, n: int = 20) -> PreviewResult:
        """Hit count plus the top `n` records, for the researcher to judge the search."""
        ...

    def search(self, spec: QuerySpec, cap: int, known_ids: frozenset[str] = frozenset()) -> SearchResult:
        """Up to `cap` results in rank order. Records whose source_record_id is in
        `known_ids` are listed in `ids` but not returned again in `records`."""
        ...
