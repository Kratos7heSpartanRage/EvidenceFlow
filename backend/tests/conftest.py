from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

# Always isolate this suite from a developer's real review database, even when
# DATABASE_URL is already configured in the invoking environment.
_test_directory = tempfile.TemporaryDirectory(prefix="evidenceflow-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_test_directory.name) / "suite.db").replace(
    "\\", "/"
)

from app.adapters.base import HttpResponse, RateLimiter


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    from app import models  # noqa: F401 -- register the complete model metadata
    from app.core.database import Base, engine

    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    _test_directory.cleanup()


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(*parts: str) -> dict[str, Any]:
    return json.loads(FIXTURES.joinpath(*parts).read_text(encoding="utf-8"))


def json_response(
    payload: Any, status: int = 200, headers: Mapping[str, str] | None = None
) -> HttpResponse:
    return HttpResponse(
        status=status, body=json.dumps(payload).encode(), headers=dict(headers or {})
    )


class FakeTransport:
    """Returns scripted responses in order and records every call."""

    def __init__(self, *responses: HttpResponse | BaseException):
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, params: Mapping[str, Any], timeout: float) -> HttpResponse:
        self.calls.append({"url": url, "params": dict(params), "timeout": timeout})
        if not self.responses:
            raise AssertionError(f"unexpected extra request: {dict(params)}")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class SleepRecorder:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


@pytest.fixture
def no_wait_limiter() -> RateLimiter:
    return RateLimiter(1_000_000, sleep=lambda _s: None)


@pytest.fixture
def sleeps() -> SleepRecorder:
    return SleepRecorder()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    import os

    if os.environ.get("EVIDENCEFLOW_LIVE") == "1":
        return
    skip_live = pytest.mark.skip(reason="live API test; set EVIDENCEFLOW_LIVE=1 to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
