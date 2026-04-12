"""verify-export CLI logic (on-disk manifest vs .txt count)."""

from __future__ import annotations

import json
from pathlib import Path

from notebooklm_export.verify_export import verify_notebook_export_dir


def _write_manifest(nb_dir: Path, *, source_count: int, sources: list) -> None:
    (nb_dir / "export_manifest.json").write_text(
        json.dumps(
            {
                "notebook_id": "00000000-0000-4000-8000-000000000001",
                "notebook_title": "Test",
                "source_count": source_count,
                "sources": sources,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_verify_ok_three_sources(tmp_path: Path) -> None:
    nb = tmp_path / "nb"
    nb.mkdir()
    _write_manifest(
        nb,
        source_count=3,
        sources=[
            {"source_id": "a", "text_file": "x.txt"},
            {"source_id": "b", "text_file": "y.txt"},
            {"source_id": "c", "text_file": "z.txt"},
        ],
    )
    (nb / "a.txt").write_text("one", encoding="utf-8")
    (nb / "b.txt").write_text("two", encoding="utf-8")
    (nb / "c.txt").write_text("three", encoding="utf-8")
    assert verify_notebook_export_dir(nb) == 0


def test_verify_fails_txt_mismatch(tmp_path: Path) -> None:
    nb = tmp_path / "nb"
    nb.mkdir()
    _write_manifest(
        nb,
        source_count=2,
        sources=[
            {"source_id": "a"},
            {"source_id": "b"},
        ],
    )
    (nb / "a.txt").write_text("one", encoding="utf-8")
    assert verify_notebook_export_dir(nb) == 1


def test_verify_one_error_one_ok(tmp_path: Path) -> None:
    nb = tmp_path / "nb"
    nb.mkdir()
    _write_manifest(
        nb,
        source_count=2,
        sources=[
            {"source_id": "a", "text_file": "a.txt"},
            {"source_id": "b", "error": {"status": "failed"}},
        ],
    )
    (nb / "a.txt").write_text("ok", encoding="utf-8")
    assert verify_notebook_export_dir(nb) == 0


def test_verify_no_manifest_exit_2(tmp_path: Path) -> None:
    nb = tmp_path / "nb"
    nb.mkdir()
    (nb / "only.txt").write_text("x", encoding="utf-8")
    assert verify_notebook_export_dir(nb) == 2
