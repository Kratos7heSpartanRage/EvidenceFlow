"""Evaluate unchanged engines on PS-named SYNERGY and EBM-NLP corpora, offline.

python backend/examples/evaluate_engines.py --output-dir docs/evaluation/checkpoint
Run prepare_evaluation_data.py first. Only aggregates and document IDs are published.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.engines import dedup, pico, screening
from app.engines.evaluation import (
    contiguous_spans,
    latency_summary,
    prf,
    ratio,
    screening_metrics,
    token_offsets,
    tokens_overlapping_spans,
)
from app.engines.types import CriterionSpec, PicoTerms, RecordLite


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def criteria(profile: dict) -> list[CriterionSpec]:
    values = [
        CriterionSpec(i + 1, code, reason=f"Published-review approximation: {code}")
        for i, code in enumerate(profile["exclusions"])
    ]
    if profile["custom_exclusion_terms"]:
        values.append(
            CriterionSpec(
                len(values) + 1,
                "custom_keyword",
                reason="Excluded report-type keyword",
                params={"terms": profile["custom_exclusion_terms"]},
            )
        )
    return values


def score_screening(rows: list[dict], config: dict) -> tuple[dict, list[dict]]:
    profiles = {p["key"]: p for p in config["synergy"]["profiles"]}
    prepared = {
        key: (criteria(p), PicoTerms(population=p["population"], intervention=p["intervention"]))
        for key, p in profiles.items()
    }
    predictions, timings = [], []
    unchanged = 0
    for row in rows:
        # Reference labels are deliberately not part of RecordLite or the engine call.
        fields = {
            key: row[key]
            for key in (
                "id",
                "title",
                "abstract",
                "doi",
                "pmid",
                "year",
                "first_author",
                "authors",
                "language",
                "pub_types",
                "mesh",
            )
        }
        record = RecordLite(**fields, source="synergy_openalex")
        rules, terms = prepared[row["review"]]
        before = record.input_hash
        start = perf_counter()
        output = screening.screen(record, rules, terms)
        timings.append(perf_counter() - start)
        repeat = screening.screen(record, rules, terms)
        unchanged += output == repeat and before == record.input_hash
        predictions.append(
            {
                "review": row["review"],
                "id": row["id"],
                "gold": row["label"],
                "prediction": output.decision,
                "strength": output.strength,
                "has_abstract": bool((row["abstract"] or "").strip()),
                "reason_present": output.criterion_id is not None
                and any(e.explanation for e in output.evidence),
                "evidence_codes": ";".join(e.code for e in output.evidence),
            }
        )
    summaries = {}
    for key in [*profiles, "pooled"]:
        selected = [p for p in predictions if key == "pooled" or p["review"] == key]
        gold, guessed = [p["gold"] for p in selected], [p["prediction"] for p in selected]
        metrics = screening_metrics(gold, guessed)
        excluded = [p for p in selected if p["prediction"] == "exclude"]
        metrics.update(
            {
                "included_reference_count": sum(gold),
                "missing_abstract_count": sum(not p["has_abstract"] for p in selected),
                "predicted_exclusions_with_reason": sum(p["reason_present"] for p in excluded),
                "predicted_exclusion_count": len(excluded),
                "all_excluded_baseline_accuracy": 1 - sum(gold) / len(gold),
                "all_excluded_baseline_positive_f1": 0.0,
            }
        )
        summaries[key] = metrics
    return {
        "reviews": summaries,
        "timing": latency_summary(timings),
        "repeatable_unchanged_calls": unchanged,
        "calls_checked": len(rows),
    }, predictions


def score_pico(rows: list[dict]) -> tuple[dict, list[dict]]:
    totals = {mode: {label: Counter() for label in "PIO"} for mode in ("I_plus_C", "I_only")}
    errors, timings = [], []
    valid_offsets = span_count = repeatable = tokens_count = 0
    for row in rows:
        text, offsets = token_offsets(row["tokens"])
        if text != row["text"]:
            raise ValueError("Prepared text and official tokens no longer match")
        tokens_count += len(offsets)
        start = perf_counter()
        output = pico.extract_pico(text, PicoTerms())
        timings.append(perf_counter() - start)
        repeatable += output == pico.extract_pico(text, PicoTerms())
        actual_spans = [s for s in output if s.status == "suggested"]
        span_count += len(actual_spans)
        valid_offsets += sum(
            0 <= s.start_char < s.end_char <= len(text)
            and text[s.start_char : s.end_char] == s.text
            for s in actual_spans
        )
        for mode, labels in totals.items():
            for label, count in labels.items():
                prediction_labels = {"I", "C"} if label == "I" and mode == "I_plus_C" else {label}
                spans = [
                    (s.start_char, s.end_char) for s in actual_spans if s.label in prediction_labels
                ]
                guessed = tokens_overlapping_spans(offsets, spans)
                truth = {index for index, value in enumerate(row[label.lower()]) if value}
                predicted_binary = [int(index in guessed) for index in range(len(offsets))]
                exact_gold, exact_pred = (
                    contiguous_spans(row[label.lower()]),
                    contiguous_spans(predicted_binary),
                )
                count.update(
                    {
                        "token_tp": len(truth & guessed),
                        "token_fp": len(guessed - truth),
                        "token_fn": len(truth - guessed),
                        "span_tp": len(exact_gold & exact_pred),
                        "span_fp": len(exact_pred - exact_gold),
                        "span_fn": len(exact_gold - exact_pred),
                        "presence_tp": int(bool(truth) and bool(guessed)),
                        "presence_fp": int(not truth and bool(guessed)),
                        "presence_fn": int(bool(truth) and not guessed),
                    }
                )
                if mode == "I_plus_C":
                    errors.append(
                        {
                            "pmid": row["pmid"],
                            "label": label,
                            "gold_tokens": len(truth),
                            "predicted_tokens": len(guessed),
                            "tp": len(truth & guessed),
                            "fp": len(guessed - truth),
                            "fn": len(truth - guessed),
                            "exact_gold_spans": len(exact_gold),
                            "exact_predicted_spans": len(exact_pred),
                            "exact_tp": len(exact_gold & exact_pred),
                        }
                    )
    results = {}
    for mode, labels in totals.items():
        per_label = {}
        combined = sum(labels.values(), Counter())
        for label, count in [*labels.items(), ("micro", combined)]:
            per_label[label] = {
                name: prf(count[f"{key}_tp"], count[f"{key}_fp"], count[f"{key}_fn"])
                for name, key in (
                    ("token", "token"),
                    ("exact_span", "span"),
                    ("label_presence", "presence"),
                )
            }
        per_label["macro_token_f1"] = sum(per_label[label]["token"]["f1"] for label in "PIO") / 3
        results[mode] = per_label
    return {
        "documents": len(rows),
        "official_tokens": tokens_count,
        "modes": results,
        "predicted_spans": span_count,
        "valid_offset_spans": valid_offsets,
        "offset_validity": ratio(valid_offsets, span_count),
        "repeatable_calls": repeatable,
        "timing": latency_summary(timings),
        "comparator_gold_metric": None,
    }, errors


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float | None) -> str:
    return "not defined" if value is None else f"{100 * value:.2f}%"


def render_report(result: dict) -> str:
    screen = result["screening"]["reviews"]
    pooled = screen["pooled"]
    pio = result["pico"]["modes"]["I_plus_C"]
    lines = [
        "# EvidenceFlow algorithm evaluation",
        "",
        f"Measured UTC: {result['measured_at_utc']}",
        "",
        "These are measurements of the unchanged deterministic engines on external datasets named in the problem statement. They are not deployment verification, a clinical validation or the organizer's unpublished scoring rubric.",
        "",
        "## Data and frozen setup",
        "",
        "- SYNERGY release 1.0: three complete medical review subsets selected before evaluating predictions. Profiles in `backend/evaluation/datasets.json` approximate published criteria using existing abstract/metadata rules. No reference labels are passed to the engines. No model was trained or tuned on these records.",
        f"- Screening: {pooled['n']} records, {pooled['included_reference_count']} included reference labels and {pooled['missing_abstract_count']} missing abstracts. References are final review inclusion decisions; not all full-text criteria can be inferred from abstracts. This is a proxy benchmark, not an equivalent full-text review.",
        f"- EBM-NLP v2: {result['pico']['documents']} documents in the intersection of expert P/I/O test files, {result['pico']['official_tokens']} official tokens. Crowd/training labels were not used. The corpus was converted locally to Parquet without executing the Hugging Face loading script.",
        "- PICO uses an empty review lexicon (cue-only baseline). Text is reconstructed with one space between official tokens. P maps to Participants; I and C predictions are unioned for the corpus's combined Interventions channel; O maps to Outcomes. I-only scores are also included in JSON. There is no separate comparator reference label.",
        "- Raw abstracts, EBM token-level annotation sequences and converted Parquet remain in Git-ignored `.eval_data/`. Public artifacts contain aggregates, openly licensed SYNERGY reference decisions/error IDs, and per-document PIO error counts without source text or EBM annotation sequences.",
        "",
        "## Screening results",
        "",
        "Only Include counts positive for strict precision/recall/F1. Maybe counts as non-Include for that strict score. The separate retention metric counts Include + Maybe as remaining for human review. It must be read together with the fraction of all records retained.",
        "",
        "| Review | N / included | Include precision | Include recall | Include F1 | Maybe | Eligible suggested Exclude |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in screen.items():
        pos = row["per_class"]["included"]
        lines.append(
            f"| {name} | {row['n']} / {row['included_reference_count']} | {pct(pos['precision'])} | {pct(pos['recall'])} | {pct(pos['f1'])} | {pct(row['maybe_rate'])} | {row['eligible_records_suggested_exclude']} |"
        )
    lines += [
        "",
        f"- Pooled strict accuracy: **{pct(pooled['accuracy'])}**; all-excluded majority baseline: **{pct(pooled['all_excluded_baseline_accuracy'])}**. High accuracy alone is weak evidence on this imbalanced set.",
        f"- Pooled strict macro F1 (Included/Excluded): **{pct(pooled['macro_f1'])}**. There is no gold Maybe class in SYNERGY.",
        f"- Eligible retention if Maybe remains for review: **{pct(pooled['eligible_retention_if_maybe_stays_for_review'])}**, while **{pct(pooled['fraction_records_retained_if_only_exclude_removed'])}** of all records remain. This is a hypothetical triage summary, not measured time saved or autonomous eligibility accuracy.",
        f"- Exclusion reason coverage: **{pooled['predicted_exclusions_with_reason']}/{pooled['predicted_exclusion_count']}** suggestions have a criterion and explanatory evidence.",
        "",
        "Pooled confusion matrix (rows: published reference; columns: engine suggestion):",
        "",
        "| Reference | Include | Exclude | Maybe |",
        "|---|---:|---:|---:|",
    ]
    for label, row in pooled["three_way_confusion"].items():
        lines.append(f"| {label} | {row['include']} | {row['exclude']} | {row['maybe']} |")
    lines += [
        "",
        "## PIO extraction results",
        "",
        "Positive-token micro precision/recall/F1 use official token positions, not matching strings. A token is predicted positive when its characters overlap a predicted span. Exact spans are contiguous positive-token runs after projection; boundaries must agree exactly. True-negative tokens are not rewarded in F1. Zero-division is 0 and TP/FP/FN counts are saved.",
        "",
        "| Channel | Token precision | Token recall | Token F1 | Exact-span F1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for label in ["P", "I", "O", "micro"]:
        values = pio[label]
        lines.append(
            f"| {label} {'(I+C union)' if label == 'I' else ''} | {pct(values['token']['precision'])} | {pct(values['token']['recall'])} | {pct(values['token']['f1'])} | {pct(values['exact_span']['f1'])} |"
        )
    lines += [
        "",
        f"- Valid original-string slices on the reconstructed benchmark text: **{result['pico']['valid_offset_spans']}/{result['pico']['predicted_spans']}**. Offset validity is a software-integrity check, not semantic correctness.",
        "- Standalone Comparator precision/recall/F1: **not measured** because the selected corpus has no separate Comparator gold labels. Do not present the Interventions score as Comparator accuracy.",
        "",
        "## Repeatability and timing",
        "",
        f"- Screening repeated identically without changing inputs: {result['screening']['repeatable_unchanged_calls']}/{result['screening']['calls_checked']}.",
        f"- PICO repeated identically: {result['pico']['repeatable_calls']}/{result['pico']['documents']}.",
    ]
    for name in ("screening", "pico"):
        timing = result[name]["timing"]
        lines.append(
            f"- {name}: {timing['calls']} pure-function calls; median {timing['median_ms']:.3f} ms, p95 {timing['p95_ms_nearest_rank']:.3f} ms, summed time {timing['total_seconds']:.3f} s. Excludes downloads, DB, API, frontend and metric calculation; not end-to-end latency."
        )
    lines += [
        "",
        "## What these results do not establish",
        "",
        "No expert deduplication pair labels were supplied by these corpora, so dedup precision/recall are not invented from record IDs. Existing unit/integration tests cover duplicate/grouping behavior separately. No manual reviewer time study was run. No confidence-calibration, deployment, live API or clinical-use claim follows from this benchmark. Subsets are a convenience selection, not a representative sample of all reviews. Read the per-review errors before generalizing.",
        "",
        "## Reproduce",
        "",
        "```powershell",
        'python -m pip install -e "backend[evaluation]"',
        "python backend/examples/prepare_evaluation_data.py --download",
        "python backend/examples/evaluate_engines.py --output-dir docs/evaluation/checkpoint",
        "```",
        "",
        "Input revisions, checksums, algorithm versions, source-file hashes, environment and exact confusion counts are recorded in `metrics.json`. The first command may require installing the project's dev dependencies separately to run tests.",
        "",
        "Sources: [SYNERGY](https://github.com/asreview/synergy-dataset), [pinned release](https://doi.org/10.34894/HE6NAQ), [EBM-NLP](https://github.com/bepnye/EBM-NLP), [BigBio dataset card](https://huggingface.co/datasets/bigbio/ebm_pico), [precision/recall/F1 conventions](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".eval_data")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/evaluation/checkpoint")
    args = parser.parse_args()
    import pyarrow
    import pyarrow.parquet as pq

    config_path = ROOT / "backend/evaluation/datasets.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    prepared = json.loads((args.data_dir / "prepared_manifest.json").read_text(encoding="utf-8"))
    if prepared["config_sha256"] != sha(config_path):
        raise ValueError(
            "Evaluation profiles changed after preparation; prepare again and document why"
        )
    for name in ("synergy.parquet", "ebm_expert_test.parquet"):
        if sha(args.data_dir / name) != prepared[name]["sha256"]:
            raise ValueError("Prepared data checksum mismatch")
    screening_result, screening_rows = score_screening(
        pq.read_table(args.data_dir / "synergy.parquet").to_pylist(), config
    )
    pico_result, pico_errors = score_pico(
        pq.read_table(args.data_dir / "ebm_expert_test.parquet").to_pylist()
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result = {
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "working_tree_commit": commit,
        "environment": {
            "python": platform.python_version(),
            "os": platform.system(),
            "pyarrow": pyarrow.__version__,
        },
        "algorithm_versions": {
            "dedup": dedup.ALGO_VERSION,
            "screening": screening.ALGO_VERSION,
            "pico": pico.ALGO_VERSION,
        },
        "engine_file_sha256": {f.name: sha(f) for f in (ROOT / "backend/app/engines").glob("*.py")},
        "runner_sha256": sha(Path(__file__)),
        "datasets": config,
        "prepared_inputs": prepared,
        "screening": screening_result,
        "pico": pico_result,
        "dedup_quality": {
            "status": "not measured",
            "reason": "No expert duplicate-pair ground truth in selected corpora",
        },
        "deployment": {
            "status": "not verified",
            "note": "User plans deployment today; no deployed URL supplied",
        },
    }
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (out / "EVALUATION_REPORT.md").write_text(render_report(result), encoding="utf-8")
    rows = []
    for review, values in screening_result["reviews"].items():
        for metric in ("precision", "recall", "f1"):
            rows.append(
                {
                    "stage": "screening",
                    "dataset": review,
                    "channel": "strict Include",
                    "metric": metric,
                    "value_fraction": values["per_class"]["included"][metric],
                    "n": values["n"],
                }
            )
    for label in ["P", "I", "O", "micro"]:
        for metric in ("precision", "recall", "f1"):
            rows.append(
                {
                    "stage": "pico",
                    "dataset": "EBM-NLP expert test",
                    "channel": label,
                    "metric": "token_" + metric,
                    "value_fraction": pico_result["modes"]["I_plus_C"][label]["token"][metric],
                    "n": pico_result["documents"],
                }
            )
    write_csv(out / "metrics.csv", rows)
    # Error diagnostics contain IDs/counts only, no abstracts, tokens or annotation sequences.
    write_csv(
        out / "screening_errors.csv",
        [p for p in screening_rows if (p["prediction"] == "include") != bool(p["gold"])],
    )
    write_csv(out / "pico_error_counts.csv", pico_errors)
    print(
        json.dumps(
            {
                "output": str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out),
                "screening": screening_result["reviews"]["pooled"],
                "pico_token_micro": pico_result["modes"]["I_plus_C"]["micro"]["token"],
                "expert_documents": pico_result["documents"],
            }
        )
    )


if __name__ == "__main__":
    main()
