# notebooklm-export — checkpoint & learnings

Last consolidated: **2026-04-12**. Use this file when picking the project back up.

## Canonical repo location

Work from **one clone** (avoid duplicating with `Projects\`):

`C:\Users\matti\OneDrive\Documents\GitHub\notebooklm-export`

Remote: `https://github.com/Taitai54/notebooklm-export` (push from here).

## What the tool is for

Batch-export NotebookLM **source text** for pipelines (e.g. **Pinecone**): one **`.txt` per source**, plus a single **`export_manifest.json`** for ids, labels, URLs, and paths to each `.txt`.

## Current default export shape

- **Always:** `*.txt` (full source body) + **`export_manifest.json`**.
- **Opt-in** (`--sidecar-json` / GUI “Per-source .json files”): duplicate metadata into one `.json` next to each `.txt` (same info is already in the manifest).
- **Opt-in** (`--summaries` / GUI “AI summaries”): `.summary.md` per source (extra MCP calls; not the raw source).
- **Opt-in** (`--studio-manifest` / GUI “Studio manifest”): `studio_status.json`.

**`export.bat`** runs plain `export` (no summaries/studio flags) unless you edit the command line.

## GUI notes

- **`notebooklm-export.bat`** with no args starts the **GUI** (not CLI help).
- **FastMCP** prints a large startup banner; the GUI **filters** those lines and sets `NO_COLOR=1` / `PYTHONUTF8=1` on the export subprocess so logs stay readable.
- Export runs: `python -m notebooklm_export export …` (same as CLI).

## Verification (no live NotebookLM needed)

```bash
pip install -e ".[dev]"
pytest -q
```

```bash
notebooklm-export verify-export "C:\path\to\<notebook_folder_slug>_<idprefix>"
```

Exit **0** = manifest’s successful source count matches number of `.txt` files. **2** = no `export_manifest.json` (re-export with a current build).

## Offline tests

- `tests/fixtures/notebook_get_five_sources.json` — wire-format sample; proves **five** sources are parsed from `notebook_get`.
- `tests/test_gui_log_filter.py` — banner noise filtering.

## Learnings / gotchas

1. **Missing `export_manifest.json` on old runs** — older exports or interrupted runs may only have `.txt`/`.json`/`.summary.md`; re-export to get a manifest for `verify-export`.
2. **`source_count` in list vs exported files** — if they match and verify passes, you got all sources the API returned in `notebook_get`.
3. **Unicode in CMD** — avoid fancy Unicode in `.bat` help strings; stick to ASCII to prevent `ÔÇö`-style mojibake.
4. **Two folders problem** — don’t maintain both `Projects\` and OneDrive clones; OneDrive + GitHub is the source of truth.
5. **Pinecone** — ingest **`.txt`** bodies; use **`export_manifest.json`** for metadata (no need for per-source `.json` unless you want it on disk).

## Quick commands

```bash
notebooklm-export list
notebooklm-export export "Notebook Title" --out "%USERPROFILE%\Documents\NotebookLM_exports"
notebooklm-export export UUID --out ./exports --sidecar-json --summaries --studio-manifest   # full optional bundle
```

## Cursor / agent

Open the **OneDrive** folder as the workspace so edits land in the repo you push.
