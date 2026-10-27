"""Save raw Europe PMC responses for comparison with the synthetic fixtures.

Run on a machine with internet access, from the repo root:

    python scripts/record_fixtures.py "metformin AND placebo" --from 2015-01-01 --to 2025-12-31

Writes backend/tests/fixtures/europe_pmc/recorded/<slug>_{synonyms-off,synonyms-on}.json
and prints the hit counts with and without MeSH synonym expansion. Uses the same
adapter code (query building, rate limiting, retries) as the application.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.adapters.base import RateLimiter, UrllibTransport, request_json  # noqa: E402
from app.adapters.europe_pmc import BASE_URL, build_query  # noqa: E402
from app.schemas.contracts import QuerySpec, SourceName  # noqa: E402

OUT_DIR = ROOT / "backend" / "tests" / "fixtures" / "europe_pmc" / "recorded"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("expression")
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat)
    parser.add_argument("--to", dest="date_to", type=date.fromisoformat)
    parser.add_argument("--page-size", type=int, default=25)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", args.expression.lower()).strip("-")[:60]
    limiter = RateLimiter(5)
    transport = UrllibTransport()

    for expand in (False, True):
        spec = QuerySpec(
            source=SourceName.EUROPE_PMC,
            expression=args.expression,
            date_from=args.date_from,
            date_to=args.date_to,
            expand_synonyms=expand,
        )
        params = {
            "query": build_query(spec),
            "format": "json",
            "resultType": "core",
            "pageSize": args.page_size,
            "cursorMark": "*",
            "synonym": "true" if expand else "false",
        }
        data = request_json(
            transport=transport, limiter=limiter, source="europe_pmc", url=BASE_URL, params=params
        )
        label = "synonyms-on" if expand else "synonyms-off"
        path = OUT_DIR / f"{slug}_{label}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{label:13} hitCount={data.get('hitCount')}  -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
