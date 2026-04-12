"""Offline checks: notebook_get wire format -> we enumerate every source."""

from __future__ import annotations

import json
from pathlib import Path

from notebooklm_export.mcp_util import (
    extract_notebook_title_from_get,
    extract_sources_from_notebook_get,
)


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "notebook_get_five_sources.json"


def test_extract_sources_five_from_fixture() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    sources = extract_sources_from_notebook_get(data)
    assert len(sources) == 5
    ids = [s[0] for s in sources]
    assert len(set(ids)) == 5
    labels = [s[1] for s in sources]
    assert "Source Alpha" in labels
    assert "Source Epsilon" in labels


def test_extract_title_from_fixture() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert extract_notebook_title_from_get(data) == "Dummy notebook (fixture)"


def test_empty_notebook_returns_no_sources() -> None:
    assert extract_sources_from_notebook_get({}) == []
    assert extract_sources_from_notebook_get({"notebook": []}) == []
