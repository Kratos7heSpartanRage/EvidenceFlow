"""Map persisted bibliographic records to the pure engines' input contract."""

from typing import Any

from app.engines.types import RecordLite


def to_engine_record(record: Any) -> RecordLite:
    authors = record.authors or []
    names = tuple(
        item.get("full_name", "") if isinstance(item, dict) else str(item) for item in authors
    )
    first = authors[0] if authors else None
    surname = first.get("last_name") if isinstance(first, dict) else None
    return RecordLite(
        id=record.id,
        title=record.title,
        abstract=record.abstract,
        source=record.source,
        doi=record.doi,
        pmid=record.pmid,
        year=record.publication_year,
        authors=names,
        first_author=surname or (names[0] if names else None),
        journal=record.journal,
        language=record.language,
        pub_types=tuple(record.publication_types or []),
        mesh=tuple(record.mesh_headings or []),
    )
