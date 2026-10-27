"""Identifier-first duplicate suggestions and deterministic graph grouping."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable
from itertools import combinations

from .normalize import normalize_author, normalize_doi, normalize_pmid, normalize_title
from .types import PairResult, RecordId, RecordLite, record_id_key

ALGO_VERSION = "dedup-rules-2"


def _conference(record: RecordLite) -> bool:
    return any(
        any(
            term in normalize_title(kind) for term in ("congress", "conference", "meeting abstract")
        )
        for kind in record.pub_types
    )


def _journal(record: RecordLite) -> bool:
    return any(normalize_title(kind) == "journal article" for kind in record.pub_types)


def _author(record: RecordLite) -> str:
    return normalize_author(record.first_author or (record.authors[0] if record.authors else None))


def _score(a: RecordLite, b: RecordLite, include_fuzzy: bool) -> PairResult | None:
    doi_a, doi_b = normalize_doi(a.doi), normalize_doi(b.doi)
    pmid_a, pmid_b = normalize_pmid(a.pmid), normalize_pmid(b.pmid)
    title_a, title_b = normalize_title(a.title), normalize_title(b.title)
    author_a, author_b = _author(a), _author(b)
    matched: list[str] = []
    conflicts: list[str] = []
    for name, first, second in (
        ("doi", doi_a, doi_b),
        ("pmid", pmid_a, pmid_b),
        ("title", title_a, title_b),
        ("first_author", author_a, author_b),
        ("year", a.year, b.year),
    ):
        if first is not None and first != "" and second is not None and second != "":
            (matched if first == second else conflicts).append(name)

    method, score, tier = "", 0.0, "uncertain"
    if doi_a and doi_a == doi_b:
        method, score, tier = "doi", 1.0, "auto"
    elif pmid_a and pmid_a == pmid_b:
        method, score, tier = "pmid", 1.0, "auto"
    elif title_a and title_a == title_b:
        if a.year is not None and b.year is not None and abs(a.year - b.year) > 1:
            return None
        method = "title_year_author"
        if a.year is not None and a.year == b.year and author_a and author_a == author_b:
            score, tier = 0.95, "auto"
        else:
            score = 0.90 if a.year is not None and b.year is not None else 0.85
    elif include_fuzzy and a.year is not None and a.year == b.year:
        first, second = set(title_a.split()), set(title_b.split())
        if len(first & second) < 3:
            return None
        score = len(first & second) / len(first | second)
        if score < 0.90:
            return None
        method = "fuzzy"
        matched.append("title_tokens")
    else:
        return None

    conference_guard = (_conference(a) and _journal(b)) or (_conference(b) and _journal(a))
    identifier_guard = "doi" in conflicts or "pmid" in conflicts
    if conference_guard:
        conflicts.append("publication_type")
    if conference_guard or identifier_guard:
        tier = "uncertain"
        explanation = "Possible separate report of the same study; reviewer confirmation required."
    elif tier == "auto":
        explanation = "Exact identifier or matching title, year, and first author."
    else:
        explanation = "Bibliographic similarity is incomplete; reviewer confirmation required."
    return PairResult(
        a.id, b.id, method, score, tier, tuple(matched), tuple(conflicts), explanation
    )


def score_pairs(
    records: list[RecordLite],
    *,
    include_fuzzy: bool = False,
    changed_ids: Iterable[RecordId] | None = None,
) -> list[PairResult]:
    """Score blocked pairs; optionally return only pairs touching changed records.

    Blocking uses DOI, PMID, or normalized title prefix with year +/- 1. Missing
    years also enter title blocks so uncertainty is surfaced rather than hidden.
    Optional fuzzy matching adds shared token/year blocks and never auto-merges.
    Large identical-title blocks can still be quadratic; imports should be capped.
    """
    by_id = {record.id: record for record in records}
    if len(by_id) != len(records):
        raise ValueError("Record ids must be unique")
    changed = None if changed_ids is None else set(changed_ids)
    if changed is not None and not changed <= by_id.keys():
        raise ValueError("Changed ids must belong to the supplied active record set")
    blocks: dict[tuple, list[RecordId]] = defaultdict(list)
    title_blocks: dict[str, list[RecordLite]] = defaultdict(list)
    for record in records:
        for kind, value in (
            ("doi", normalize_doi(record.doi)),
            ("pmid", normalize_pmid(record.pmid)),
        ):
            if value:
                blocks[kind, value].append(record.id)
        title = normalize_title(record.title)
        if title:
            title_blocks[title[:30]].append(record)
        if include_fuzzy and record.year is not None:
            for token in set(title.split()):
                blocks["token_year", token, record.year].append(record.id)
    candidates: set[tuple[RecordId, RecordId]] = set()
    for members in blocks.values():
        candidates.update(combinations(sorted(members, key=record_id_key), 2))
    for members in title_blocks.values():
        for a, b in combinations(members, 2):
            if a.year is None or b.year is None or abs(a.year - b.year) <= 1:
                candidates.add(tuple(sorted((a.id, b.id), key=record_id_key)))
    result = []
    for a_id, b_id in sorted(
        candidates, key=lambda pair: (record_id_key(pair[0]), record_id_key(pair[1]))
    ):
        if changed is not None and a_id not in changed and b_id not in changed:
            continue
        pair = _score(by_id[a_id], by_id[b_id], include_fuzzy)
        if pair is not None:
            result.append(pair)
    return result


def group(
    record_ids: Iterable[RecordId], edges: Iterable[tuple[RecordId, RecordId]]
) -> list[set[RecordId]]:
    """Connected components, including singleton records, in stable id order."""
    ids = set(record_ids)
    adjacency = {record_id: set() for record_id in ids}
    for a_id, b_id in edges:
        if a_id not in ids or b_id not in ids:
            raise ValueError("Every edge endpoint must be in the active record set")
        if a_id == b_id:
            raise ValueError("Self edges are invalid")
        adjacency[a_id].add(b_id)
        adjacency[b_id].add(a_id)
    remaining = set(ids)
    groups = []
    while remaining:
        pending, members = [min(remaining, key=record_id_key)], set()
        while pending:
            current = pending.pop()
            if current not in members:
                members.add(current)
                pending.extend(adjacency[current] - members)
        groups.append(members)
        remaining -= members
    return groups


def group_key(record_ids: Iterable[RecordId]) -> str:
    """Membership key compatible with the blueprint's immutable snapshots."""
    members = sorted(set(record_ids), key=record_id_key)
    if not members:
        raise ValueError("A group cannot be empty")
    return hashlib.sha1(",".join(map(str, members)).encode("utf-8")).hexdigest()


def group_with_rejections(
    record_ids: Iterable[RecordId],
    edges: Iterable[tuple[RecordId, RecordId]],
    rejected_edges: Iterable[tuple[RecordId, RecordId]],
    *,
    preferred_edges: Iterable[tuple[RecordId, RecordId]] = (),
) -> tuple[list[set[RecordId]], list[tuple[RecordId, RecordId]]]:
    """Deterministically partition a proposed graph with human cannot-links.

    Human-confirmed preferred edges are considered first. An edge that would
    bridge a rejection is held back and the violated rejection is returned for
    conflict review. A rejection is never silently overridden or resolved.
    """
    ids = set(record_ids)

    def pair_key(pair):
        return record_id_key(pair[0]), record_id_key(pair[1])

    def canonical(pair):
        return tuple(sorted(pair, key=record_id_key))

    edges = {canonical(pair) for pair in edges}
    rejected = {canonical(pair) for pair in rejected_edges}
    preferred = {canonical(pair) for pair in preferred_edges}
    group(ids, edges | rejected | preferred)  # validates all endpoints and self edges
    root = {record_id: record_id for record_id in ids}
    members = {record_id: {record_id} for record_id in ids}

    def find(record_id):
        while root[record_id] != record_id:
            record_id = root[record_id]
        return record_id

    blocked = set()
    for a, b in sorted(edges - rejected, key=lambda pair: (pair not in preferred, pair_key(pair))):
        left, right = find(a), find(b)
        if left == right:
            continue
        violations = {
            pair
            for pair in rejected
            if (
                (pair[0] in members[left] and pair[1] in members[right])
                or (pair[1] in members[left] and pair[0] in members[right])
            )
        }
        if violations:
            blocked.update(violations)
            continue
        keep, discard = sorted((left, right), key=record_id_key)
        root[discard] = keep
        members[keep].update(members[discard])
    components = {}
    for record_id in sorted(ids, key=record_id_key):
        components.setdefault(find(record_id), set()).add(record_id)
    return list(components.values()), sorted(blocked, key=pair_key)


def representative(records: Iterable[RecordLite], pinned_ids: Iterable[RecordId] = ()) -> RecordId:
    """Pin first, then abstract, DOI, PubMed, and lowest stable record id."""
    values, pins = list(records), set(pinned_ids)
    if not values:
        raise ValueError("A group cannot be empty")
    return min(
        values,
        key=lambda r: (
            r.id not in pins,
            not bool((r.abstract or "").strip()),
            not bool(normalize_doi(r.doi)),
            r.source.casefold() != "pubmed",
            record_id_key(r.id),
        ),
    ).id
