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

Export one notebook (text + per-source JSON metadata + manifest):

```bash
notebooklm-export export NOTEBOOK_UUID --out ./exports
notebooklm-export export NOTEBOOK_UUID --out ./exports --summaries --studio-manifest
```

Module form:

```bash
python -m notebooklm_export list
python -m notebooklm_export export NOTEBOOK_UUID --out ./exports
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
