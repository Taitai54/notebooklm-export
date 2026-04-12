# notebooklm-export

Export **raw source text**, optional **AI source summaries**, and **Studio artifact metadata** from a NotebookLM notebook using the official [`notebooklm-mcp`](https://www.npmjs.com/package/notebooklm-mcp) server over stdio.

This tool starts its **own** short-lived MCP process. It does not replace or conflict with Cursor’s NotebookLM MCP.

## Setup

1. Install Node’s `notebooklm-mcp` globally or use `npx`, and authenticate once:

   ```bash
   npx notebooklm-mcp-auth
   ```

   Tokens are stored under `~/.notebooklm-mcp/auth.json` (Windows: `%USERPROFILE%\.notebooklm-mcp\auth.json`).

2. Install this package:

   ```bash
   cd notebooklm-export
   pip install -e .
   ```

## Configure the MCP command

Match whatever you use in Cursor (default: `notebooklm-mcp` on `PATH`):

```powershell
$env:NOTEBOOKLM_MCP_COMMAND = "npx"
$env:NOTEBOOKLM_MCP_ARGS = "-y notebooklm-mcp"
```

## Usage

List notebooks (IDs and titles):

```bash
notebooklm-export list
notebooklm-export list --json
notebooklm-export list --max-results 500
```

Export one notebook (text + per-source JSON metadata + manifest).

Use the **UUID**, or the **notebook title** (case-insensitive exact match; if that is not unique, a **unique substring** of the title):

```bash
notebooklm-export export cf0de99f-b8fc-4014-b26c-647cd2a0d431 --out ./exports
notebooklm-export export "December" --out ./exports
notebooklm-export export "HMRC Tax Strategy" --out ./exports --summaries --studio-manifest
```

If you have more than 500 notebooks, raise the list fetch limit when resolving by name:

```bash
notebooklm-export export "My Title" --list-max-results 2000 --out ./exports
```

Module form:

```bash
python -m notebooklm_export list
python -m notebooklm_export export NOTEBOOK_UUID --out ./exports
```

On Windows, from this repo folder you can use the launcher (same arguments as above):

```bat
notebooklm-export.bat list
notebooklm-export.bat export "My Notebook" --out .\exports
```

**Double-click behavior:** If you double-click `notebooklm-export.bat` with no arguments, it **starts the graphical exporter** (same as `export-gui.bat`). This window shows a short tip, then closes after a couple of seconds while the GUI runs in another window. For the CLI only, open Command Prompt in this folder and run `notebooklm-export.bat list` (or `export`, etc.).

For **`export.bat`**: you can either set `NOTEBOOK=` in the file to your **title or UUID**, or leave the placeholder — the script will **ask you to type the title or UUID** when you run it. It runs `pip install -e .` against this folder if needed (using `"%~dp0."` so paths with spaces work), sets **`PYTHONUNBUFFERED=1`** so the window does not look “stuck” during long exports, then writes under **`exports`** next to the scripts. At the end it lists that folder and waits for a key so you can read any errors.

### GUI (pick notebooks to export)

Uses **Tkinter** (included with Python on Windows). After `pip install -e .`:

```bash
notebooklm-export-gui
# or
python -m notebooklm_export.gui
```

Or double-click **`export-gui.bat`** in this folder (opens a new window).

1. Click **Refresh list** to load notebooks from NotebookLM (same MCP auth as the CLI).
2. **Ctrl+click** or **Shift+click** to select one or many rows.
3. Choose an **export folder** (default: `Documents\NotebookLM_exports`).
4. Toggle **summaries** / **studio manifest** if you want.
5. **Export selected** runs the existing `export` command once per notebook and streams the log in the window.

The GUI is a thin wrapper: it shells out to `python -m notebooklm_export …`, so behavior matches the terminal tool.

### Verify exports (all sources → `.txt` for Pinecone, etc.)

After an export, each successful source produces one **`.txt`** in the notebook folder. The exporter also writes **`export_manifest.json`** listing every source (including any MCP errors). Check that counts line up **without** talking to NotebookLM:

```bash
notebooklm-export verify-export "C:\path\to\Notebook_folder_slug_UUIDprefix"
notebooklm-export verify-export "C:\path\to\NotebookLM_exports"   # if exactly one notebook subfolder
notebooklm-export verify-export .\exports\MyNotebook_abc12345 --json
```

Exit code **0** = manifest says *N* successes and the folder has *N* `.txt` files. **2** = no manifest (re-export with a current build so the manifest is written).

### Dummy notebook (manual end-to-end)

This repo cannot create notebooks without your Google session. To sanity-check a **live** export:

1. In **NotebookLM**, create a notebook and add **several** pasted-text or URL sources (give them obvious titles).
2. Run **`notebooklm-export list`** and confirm **source count** matches what you added.
3. **Export** that notebook, then **`notebooklm-export verify-export`** on the output folder.

Optional: Cursor’s **NotebookLM MCP** includes `notebook_create` and `notebook_add_text` if you want to script a throwaway notebook (same auth as the CLI).

### Automated tests (offline)

The parser is tested against a **fixture** that mimics `notebook_get` with **five** sources (no network). From the repo root:

```bash
pip install -e ".[dev]"
pytest -q
```

Discover MCP tool names (like a dry-run discovery pass):

```bash
notebooklm-export discover
notebooklm-export discover --json
```

Ask the notebook one question (uses `notebook_query`; answers are **generated**, not raw sources):

```bash
notebooklm-export ask NOTEBOOK_UUID "What are the main themes across my sources?"
```

Batch questions (one per line) to JSONL for ingestion:

```bash
notebooklm-export ask-batch NOTEBOOK_UUID questions.txt --out ./qa.jsonl
notebooklm-export ask-batch NOTEBOOK_UUID questions.txt --out ./qa.jsonl --follow-up
```

## Output layout

```
exports/
  <notebook-title-slug>_<short-id>/
    export_manifest.json
    studio_status.json          # if --studio-manifest
    <source-slug>.txt
    <source-slug>.json
    <source-slug>.summary.md    # if --summaries
```

`studio_status.json` contains URLs for generated assets when the API provides them. Downloading binaries may require separate authenticated HTTP (cookies); this exporter saves metadata and leaves downloads to you.

## Database loading

- Ingest `export_manifest.json` and each `*.json` next to sources for structured fields.
- Store `content` from the `.txt` files (or load file paths only).

## License

MIT
