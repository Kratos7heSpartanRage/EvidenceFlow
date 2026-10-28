"""Preparation tests use invented bytes, never downloaded corpus text."""

import hashlib
import io
import tarfile

import pytest

from examples.prepare_evaluation_data import abstract_text, ebm_rows, ensure_file


def test_openalex_inverted_index_reconstruction_and_invalid_positions():
    assert abstract_text({"second": [1], "first": [0, 2]}) == "first second first"
    assert abstract_text(None) is None
    with pytest.raises(ValueError):
        abstract_text({"a": [0], "b": [0]})


def test_cached_download_is_verified_and_does_not_touch_network(tmp_path):
    path = tmp_path / "data.txt"
    path.write_bytes(b"invented")
    item = {"sha256": hashlib.sha256(b"invented").hexdigest()}
    ensure_file(path, item, download=False)
    with pytest.raises(ValueError):
        ensure_file(path, {"sha256": "wrong"}, download=False)
    with pytest.raises(FileNotFoundError):
        ensure_file(tmp_path / "missing", item, download=False)


def test_ebm_uses_only_complete_expert_gold_and_never_executes_archive_members(tmp_path):
    path = tmp_path / "tiny.tar.gz"
    entries = {
        "ebm_nlp_2_00/documents/1.tokens": "Adults\nreceived\ntherapy\n",
        "ebm_nlp_2_00/documents/2.tokens": "Other\ntext\n",
        "../../unexpected.py": "raise AssertionError('must never execute')",
    }
    for channel in ("participants", "interventions", "outcomes"):
        entries[
            f"ebm_nlp_2_00/annotations/aggregated/starting_spans/{channel}/test/gold/1.AGGREGATED.ann"
        ] = "1\n0\n0\n"
        entries[
            f"ebm_nlp_2_00/annotations/aggregated/starting_spans/{channel}/test/crowd/2.AGGREGATED.ann"
        ] = "1\n0\n"
    with tarfile.open(path, "w:gz") as archive:
        for name, value in entries.items():
            raw = value.encode()
            member = tarfile.TarInfo(name)
            member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
    rows, details = ebm_rows(path)
    assert len(rows) == details["complete_expert_documents"] == 1
    assert rows[0]["pmid"] == "1" and rows[0]["text"] == "Adults received therapy"
    assert not (tmp_path.parent / "unexpected.py").exists()
