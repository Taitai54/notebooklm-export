"""Check an on-disk export folder against export_manifest.json (completeness for Pinecone prep)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def verify_notebook_export_dir(nb_dir: Path, *, json_out: bool = False) -> int:
    """
    Return 0 if the folder looks complete, 1 on hard mismatch, 2 if no manifest (cannot fully verify).

    Expects ``nb_dir`` to be the per-notebook folder (contains ``export_manifest.json`` and source files).
    """
    nb_dir = nb_dir.resolve()
    lines: list[str] = []
    payload: dict[str, Any] = {"ok": False, "notebook_dir": str(nb_dir), "issues": []}

    if not nb_dir.is_dir():
        msg = f"Not a directory: {nb_dir}"
        if json_out:
            print(json.dumps({**payload, "issues": [msg]}, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 1

    manifest_path = nb_dir / "export_manifest.json"
    txt_files = sorted(nb_dir.glob("*.txt"))

    if not manifest_path.is_file():
        msg = (
            f"No export_manifest.json in {nb_dir}. "
            f"Found {len(txt_files)} .txt file(s). "
            "Re-export with the current notebooklm-export (finishes with manifest write) for automated verification."
        )
        lines.append(msg)
        payload["issues"].append(msg)
        payload["txt_files_found"] = len(txt_files)
        if json_out:
            print(json.dumps(payload, indent=2))
        else:
            print("\n".join(lines))
        return 2

    try:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in export_manifest.json: {e}"
        if json_out:
            print(json.dumps({**payload, "issues": [msg]}, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 1

    declared = manifest.get("source_count")
    entries = manifest.get("sources")
    if not isinstance(entries, list):
        msg = "export_manifest.json: missing or invalid 'sources' list"
        lines.append(msg)
        payload["issues"].append(msg)
        if json_out:
            print(json.dumps({**payload, "issues": payload["issues"]}, indent=2))
        else:
            print("\n".join(lines), file=sys.stderr)
        return 1

    ok_entries = [s for s in entries if isinstance(s, dict) and "error" not in s]
    err_entries = [s for s in entries if isinstance(s, dict) and "error" in s]

    n_ok = len(ok_entries)
    n_err = len(err_entries)
    n_txt = len(txt_files)

    payload.update(
        {
            "notebook_id": manifest.get("notebook_id"),
            "notebook_title": manifest.get("notebook_title"),
            "declared_source_count": declared,
            "manifest_entries": len(entries),
            "exported_ok": n_ok,
            "exported_errors": n_err,
            "txt_files": n_txt,
        }
    )

    if declared is not None and int(declared) != len(entries):
        msg = f"source_count ({declared}) != len(sources) ({len(entries)}) in manifest (corrupt manifest?)"
        lines.append(msg)
        payload["issues"].append(msg)

    if n_ok + n_err != len(entries):
        msg = "Some manifest entries are not dicts or are malformed"
        lines.append(msg)
        payload["issues"].append(msg)

    if n_ok != n_txt:
        msg = (
            f"Mismatch: {n_ok} successful source(s) in manifest but {n_txt} .txt file(s) in folder "
            "(each successful export should produce one .txt)."
        )
        lines.append(msg)
        payload["issues"].append(msg)

    exit_code = 0
    if payload["issues"]:
        exit_code = 1
    else:
        lines.append(
            f"OK: {n_ok} source(s) exported, {n_txt} .txt file(s), "
            f"{n_err} error(s) in manifest."
        )
        payload["ok"] = True

    if json_out:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("\n".join(lines))

    return exit_code


def run_verify_export_cli(export_dir: Path, *, json_out: bool = False) -> int:
    """Accept either the notebook subfolder or the export root containing one notebook folder."""
    export_dir = export_dir.resolve()
    if (export_dir / "export_manifest.json").is_file():
        return verify_notebook_export_dir(export_dir, json_out=json_out)
    manifests = sorted(export_dir.glob("*/export_manifest.json"))
    if len(manifests) == 1:
        return verify_notebook_export_dir(manifests[0].parent, json_out=json_out)
    if len(manifests) > 1:
        msg = f"Multiple notebook folders with export_manifest.json ({len(manifests)}). Pass one folder explicitly."
        if json_out:
            print(json.dumps({"ok": False, "issues": [msg]}, indent=2))
        else:
            print(msg, file=sys.stderr)
        return 2
    # Export root with no subfolder manifests, or a single notebook folder missing manifest: still run checks
    return verify_notebook_export_dir(export_dir, json_out=json_out)
