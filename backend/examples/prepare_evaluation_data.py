"""Prepare PS-named corpora locally; no upstream Python is executed or redistributed.

Run from any directory: python backend/examples/prepare_evaluation_data.py --download
Requires the optional evaluation dependency: pip install -e "backend[evaluation]".
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "backend/evaluation/datasets.json"


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def ensure_file(path: Path, item: dict, download: bool) -> None:
    checksum = item.get("checksum", {"type": "SHA-256", "value": item.get("sha256")})
    algorithm = checksum["type"].replace("-", "").lower()
    if not path.exists():
        if not download:
            raise FileNotFoundError(f"Missing {path.name}; rerun with --download")
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(item["url"], headers={"User-Agent": "EvidenceFlow-eval/1"})
        # Download to a partial file so interrupted responses cannot become valid cache entries.
        partial = path.with_suffix(path.suffix + ".partial")
        with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                output.write(chunk)
        if digest(partial, algorithm) != checksum["value"]:
            raise ValueError(f"Checksum mismatch for {path.name}")
        partial.replace(path)
    if digest(path, algorithm) != checksum["value"]:
        raise ValueError(f"Checksum mismatch for {path.name}")


def abstract_text(index: dict | None) -> str | None:
    if not index:
        return None
    words = {}
    for word, positions in index.items():
        for position in positions:
            if position < 0 or position in words:
                raise ValueError("Invalid OpenAlex abstract positions")
            words[position] = word
    return " ".join(words.get(i, "") for i in range(max(words) + 1))


def synergy_rows(folder: Path, review: str) -> list[dict]:
    with (folder / "labels.csv").open(encoding="utf-8-sig", newline="") as source:
        labels = list(csv.DictReader(source))
    works = {}
    with zipfile.ZipFile(folder / "works_1.zip") as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".json"):
                continue
            # Read bytes directly: never extract archive paths into the filesystem.
            for work in json.loads(archive.read(name)):
                if work["id"] in works:
                    raise ValueError("Duplicate work in SYNERGY archive")
                works[work["id"]] = work
    if len({row["openalex_id"] for row in labels}) != len(labels):
        raise ValueError("Duplicate SYNERGY reference ID")
    if set(works) != {row["openalex_id"] for row in labels}:
        raise ValueError("SYNERGY labels and works do not match exactly")
    result = []
    for row in sorted(labels, key=lambda row: row["openalex_id"]):
        work = works[row["openalex_id"]]
        label = int(row["label_included"])
        if label not in (0, 1):
            raise ValueError("Unknown SYNERGY label")
        authors = [a.get("author", {}).get("display_name", "") for a in work.get("authorships", [])]
        result.append(
            {
                "review": review,
                "id": work["id"],
                "title": work.get("title") or "",
                "abstract": abstract_text(work.get("abstract_inverted_index")),
                "doi": work.get("doi"),
                "pmid": row["pmid"] or None,
                "year": work.get("publication_year"),
                "authors": authors,
                "first_author": authors[0] if authors else None,
                "language": work.get("language"),
                # OpenAlex's broad work type is not a PubMed publication-type field.
                "pub_types": [],
                "mesh": [
                    x["descriptor_name"] for x in work.get("mesh", []) if x.get("descriptor_name")
                ],
                "label": label,
            }
        )
    return result


def ebm_rows(path: Path) -> tuple[list[dict], dict]:
    tokens, gold = {}, {name: {} for name in ("participants", "interventions", "outcomes")}
    token_pattern = re.compile(r"ebm_nlp_2_00/documents/(\d+)\.tokens$")
    label_pattern = re.compile(
        r"ebm_nlp_2_00/annotations/aggregated/starting_spans/"
        r"(participants|interventions|outcomes)/test/gold/(\d+)\.AGGREGATED\.ann$"
    )
    # A single streaming pass avoids repeated decompression of this large tar file.
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            token_match, label_match = (
                token_pattern.fullmatch(member.name),
                label_pattern.fullmatch(member.name),
            )
            if not member.isfile() or not (token_match or label_match):
                continue
            value = archive.extractfile(member).read().decode("utf-8")
            if token_match:
                tokens[token_match[1]] = value.splitlines()
            else:
                gold[label_match[1]][label_match[2]] = [int(v) for v in value.split()]
    common = set.intersection(*(set(x) for x in gold.values()))
    rows = []
    for pmid in sorted(common, key=int):
        values = tokens[pmid]
        if not values or any(not token for token in values):
            raise ValueError(f"Empty EBM token in {pmid}")
        labels = {letter: gold[name][pmid] for letter, name in zip("PIO", gold, strict=True)}
        if any(len(value) != len(values) or not set(value) <= {0, 1} for value in labels.values()):
            raise ValueError(f"EBM token/label alignment failed for {pmid}")
        rows.append(
            {
                "pmid": pmid,
                "text": " ".join(values),
                "tokens": values,
                "p": labels["P"],
                "i": labels["I"],
                "o": labels["O"],
                "split": "expert_test",
            }
        )
    return rows, {
        "expert_files_by_label": {name: len(values) for name, values in gold.items()},
        "complete_expert_documents": len(rows),
        "selection": "intersection of P/I/O expert test IDs",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download", action="store_true", help="Explicitly permit public corpus downloads"
    )
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".eval_data")
    args = parser.parse_args()
    import pyarrow as pa
    import pyarrow.parquet as pq

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    root = args.data_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest = {"config_sha256": digest(CONFIG), "pyarrow_version": pa.__version__, "inputs": []}
    for item in config["synergy"]["files"]:
        path = root / "synergy" / item["review"] / item["filename"]
        ensure_file(path, item, args.download)
        manifest["inputs"].append({"file": str(path.relative_to(root)), "sha256": digest(path)})
    ebm = config["ebm_nlp"]
    archive = root / ebm["filename"]
    ensure_file(archive, ebm, args.download)
    manifest["inputs"].append({"file": ebm["filename"], "sha256": digest(archive)})
    screening = []
    for profile in config["synergy"]["profiles"]:
        screening.extend(synergy_rows(root / "synergy" / profile["key"], profile["key"]))
    pico, details = ebm_rows(archive)
    for name, rows in (("synergy.parquet", screening), ("ebm_expert_test.parquet", pico)):
        path = root / name
        pq.write_table(pa.Table.from_pylist(rows), path, compression="zstd")
        manifest[name] = {"rows": len(rows), "sha256": digest(path)}
    manifest["ebm"] = details
    manifest["privacy"] = (
        "All raw text, labels and converted Parquet stay local; do not commit .eval_data"
    )
    (root / "prepared_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"synergy_records": len(screening), "ebm_expert_documents": len(pico), **details}
        )
    )


if __name__ == "__main__":
    main()
