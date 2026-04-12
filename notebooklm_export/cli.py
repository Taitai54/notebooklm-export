"""CLI: list notebooks and export sources + optional studio metadata via NotebookLM MCP."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from notebooklm_export.verify_export import run_verify_export_cli
from notebooklm_export.mcp_util import (
    McpStdioConfig,
    extract_notebook_title_from_get,
    extract_sources_from_notebook_get,
    first_text_block,
    load_mcp_stdio_config,
    looks_like_notebook_uuid,
    parse_notebook_list,
    parse_tool_json,
    resolve_notebook_ref,
    slugify,
)


def _rel_or_abs(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


async def call_tool_json(session: ClientSession, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    res = await session.call_tool(name, arguments)
    return parse_tool_json(first_text_block(res))


async def resolve_notebook_id(
    session: ClientSession,
    ref: str,
    list_max_results: int,
) -> tuple[str | None, str]:
    """
    Return (notebook_id, side_message). side_message is stderr log on success-by-name,
    or empty when ref was already a UUID. On failure, notebook_id is None and message is error.
    """
    ref = ref.strip()

    if looks_like_notebook_uuid(ref):
        return ref, ""

    payload = await call_tool_json(session, "notebook_list", {"max_results": list_max_results})
    if payload.get("status") != "success":
        return None, f"notebook_list failed: {json.dumps(payload, indent=2, default=str)}"

    notebooks = parse_notebook_list(payload)
    nid, msg = resolve_notebook_ref(notebooks, ref)
    return nid, msg


async def run_list(session: ClientSession, args: argparse.Namespace) -> int:
    payload = await call_tool_json(session, "notebook_list", {"max_results": args.max_results})
    notebooks = parse_notebook_list(payload)
    if payload.get("status") != "success":
        print(f"notebook_list failed: {json.dumps(payload, indent=2, default=str)}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"notebooks": notebooks}, indent=2, default=str))
        return 0

    print(f"Found {len(notebooks)} notebook(s).\n")
    for nb in notebooks:
        nb_id = nb.get("id", "")
        title = nb.get("title", "(no title)")
        src_n = nb.get("source_count", "?")
        print(f"{nb_id}\t{title}\t(sources: {src_n})")
    return 0


async def run_export(session: ClientSession, args: argparse.Namespace) -> int:
    notebook_id, res_msg = await resolve_notebook_id(
        session,
        args.notebook_ref,
        args.list_max_results,
    )
    if notebook_id is None:
        print(res_msg, file=sys.stderr)
        return 1
    if res_msg:
        print(res_msg, file=sys.stderr)

    out_root = Path(args.out).resolve()

    details = await call_tool_json(session, "notebook_get", {"notebook_id": notebook_id})
    if details.get("status") != "success":
        print(f"notebook_get failed: {json.dumps(details, indent=2, default=str)}", file=sys.stderr)
        return 1

    title = extract_notebook_title_from_get(details) or notebook_id
    sources = extract_sources_from_notebook_get(details)
    if not sources:
        print(
            "No sources parsed from notebook_get; the API shape may have changed.",
            file=sys.stderr,
        )
        return 1

    folder_name = f"{slugify(title)}_{notebook_id[:8]}"
    nb_dir = out_root / folder_name
    nb_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "notebook_id": notebook_id,
        "notebook_title": title,
        "source_count": len(sources),
        "sources": [],
    }

    for source_id, label in sources:
        await asyncio.sleep(args.delay)
        payload = await call_tool_json(session, "source_get_content", {"source_id": source_id})
        if payload.get("status") != "success":
            manifest["sources"].append(
                {"source_id": source_id, "label": label, "error": payload},
            )
            continue

        base = slugify(f"{label}_{source_id[:8]}")
        txt_path = nb_dir / f"{base}.txt"

        text_body = payload.get("content") or ""
        txt_path.write_text(text_body, encoding="utf-8")

        meta: dict[str, Any] = {
            "notebook_id": notebook_id,
            "notebook_title": title,
            "source_id": source_id,
            "label": label,
            "title": payload.get("title"),
            "source_type": payload.get("source_type"),
            "char_count": payload.get("char_count"),
            "url": payload.get("url"),
            "text_file": _rel_or_abs(txt_path, out_root),
        }

        if args.summaries:
            await asyncio.sleep(args.delay)
            summ = await call_tool_json(session, "source_describe", {"source_id": source_id})
            summ_path = nb_dir / f"{base}.summary.md"
            if summ.get("status") == "success" and summ.get("summary"):
                summ_path.write_text(str(summ["summary"]), encoding="utf-8")
                meta["summary_file"] = _rel_or_abs(summ_path, out_root)

        if args.sidecar_json:
            (nb_dir / f"{base}.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        manifest["sources"].append(meta)

    if args.studio_manifest:
        await asyncio.sleep(args.delay)
        studio = await call_tool_json(session, "studio_status", {"notebook_id": notebook_id})
        (nb_dir / "studio_status.json").write_text(
            json.dumps(studio, indent=2, default=str),
            encoding="utf-8",
        )

    (nb_dir / "export_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    ok = sum(1 for s in manifest["sources"] if "error" not in s)
    print(f"Exported {ok}/{len(sources)} sources to {nb_dir}")
    return 0 if ok == len(sources) else 2


async def run_ask(session: ClientSession, args: argparse.Namespace) -> int:
    notebook_id, res_msg = await resolve_notebook_id(
        session,
        args.notebook_ref,
        args.list_max_results,
    )
    if notebook_id is None:
        print(res_msg, file=sys.stderr)
        return 1
    if res_msg:
        print(res_msg, file=sys.stderr)

    arguments: dict[str, Any] = {
        "notebook_id": notebook_id,
        "query": args.query,
    }
    if args.timeout is not None:
        arguments["timeout"] = args.timeout
    payload = await call_tool_json(session, "notebook_query", arguments)
    text = json.dumps(payload, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0 if payload.get("status") == "success" else 1


async def run_ask_batch(session: ClientSession, args: argparse.Namespace) -> int:
    notebook_id, res_msg = await resolve_notebook_id(
        session,
        args.notebook_ref,
        args.list_max_results,
    )
    if notebook_id is None:
        print(res_msg, file=sys.stderr)
        return 1
    if res_msg:
        print(res_msg, file=sys.stderr)

    qpath = Path(args.questions_file)
    lines = [ln.strip() for ln in qpath.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    conv_id: str | None = None
    for i, question in enumerate(lines):
        await asyncio.sleep(args.delay)
        arguments: dict[str, Any] = {
            "notebook_id": notebook_id,
            "query": question,
        }
        if args.timeout is not None:
            arguments["timeout"] = args.timeout
        if conv_id:
            arguments["conversation_id"] = conv_id
        payload = await call_tool_json(session, "notebook_query", arguments)
        record = {"index": i, "question": question, "response": payload}
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

        if args.follow_up and isinstance(payload, dict):
            cid = payload.get("conversation_id")
            if isinstance(cid, str) and cid:
                conv_id = cid

    print(f"Wrote {len(lines)} Q&A record(s) to {out_path}")
    return 0


async def _verify_export_unreachable(_session: ClientSession, _args: argparse.Namespace) -> int:  # pragma: no cover
    raise RuntimeError("verify-export is handled before MCP connect; this is a bug")


async def run_discover(_session: ClientSession, args: argparse.Namespace) -> int:
    """Print MCP tool names (same idea as ENABLE_DOWNLOAD=False in the original snippet)."""
    tools = await _session.list_tools()
    if args.json:
        print(
            json.dumps(
                [{"name": t.name, "description": t.description} for t in tools.tools],
                indent=2,
            )
        )
        return 0
    print("Available MCP tools:\n")
    for t in tools.tools:
        desc = (t.description or "").replace("\n", " ")
        print(f"  {t.name}\n      {desc}\n")
    return 0


async def amain(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="NotebookLM bulk export via stdio MCP (notebooklm-mcp).",
    )
    parser.add_argument(
        "--mcp-command",
        help="Override NOTEBOOKLM_MCP_COMMAND (default: notebooklm-mcp)",
    )
    parser.add_argument(
        "--mcp-args",
        help='Override NOTEBOOKLM_MCP_ARGS (space-separated, e.g. "-y notebooklm-mcp")',
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List notebooks (id, title, source count)")
    p_list.add_argument("--max-results", type=int, default=200, help="Max notebooks to return")
    p_list.add_argument("--json", action="store_true", help="Machine-readable JSON")
    p_list.set_defaults(func=run_list)

    p_exp = sub.add_parser("export", help="Export all sources for one notebook")
    p_exp.add_argument(
        "notebook_ref",
        help="Notebook UUID, or title (exact case-insensitive match, else unique substring)",
    )
    p_exp.add_argument(
        "--list-max-results",
        type=int,
        default=500,
        metavar="N",
        help="When resolving by name, max notebooks to fetch (default: 500)",
    )
    p_exp.add_argument("--out", default="./notebooklm_exports", help="Output root directory")
    p_exp.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Seconds between MCP calls per source",
    )
    p_exp.add_argument(
        "--summaries",
        action="store_true",
        help="Also call source_describe and write .summary.md per source (off by default)",
    )
    p_exp.add_argument(
        "--sidecar-json",
        action="store_true",
        help="Write one .json metadata file per source next to each .txt (default: off; same fields are in export_manifest.json)",
    )
    p_exp.add_argument(
        "--studio-manifest",
        action="store_true",
        help="Write studio_status.json (generated asset metadata / URLs)",
    )
    p_exp.set_defaults(func=run_export)

    p_dis = sub.add_parser("discover", help="Print tool names from the connected MCP server")
    p_dis.add_argument("--json", action="store_true")
    p_dis.set_defaults(func=run_discover)

    p_ver = sub.add_parser(
        "verify-export",
        help="Check an export folder against export_manifest.json (no MCP; for batch/Pinecone QA)",
    )
    p_ver.add_argument(
        "path",
        type=Path,
        help="Notebook export folder (contains export_manifest.json) or export root with one notebook subfolder",
    )
    p_ver.add_argument("--json", action="store_true", help="Machine-readable result on stdout")
    p_ver.set_defaults(func=_verify_export_unreachable)

    p_ask = sub.add_parser(
        "ask",
        help="Run one notebook_query (model answer grounded in existing sources)",
    )
    p_ask.add_argument(
        "notebook_ref",
        help="Notebook UUID, or title (exact case-insensitive match, else unique substring)",
    )
    p_ask.add_argument(
        "--list-max-results",
        type=int,
        default=500,
        metavar="N",
        help="When resolving by name, max notebooks to fetch (default: 500)",
    )
    p_ask.add_argument("query", help="Question text")
    p_ask.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Optional timeout seconds (server default if omitted)",
    )
    p_ask.add_argument("--out", help="Write JSON response to this file instead of stdout")
    p_ask.set_defaults(func=run_ask)

    p_batch = sub.add_parser(
        "ask-batch",
        help="Run notebook_query for each non-empty line in a UTF-8 text file (JSONL output)",
    )
    p_batch.add_argument(
        "notebook_ref",
        help="Notebook UUID, or title (exact case-insensitive match, else unique substring)",
    )
    p_batch.add_argument(
        "--list-max-results",
        type=int,
        default=500,
        metavar="N",
        help="When resolving by name, max notebooks to fetch (default: 500)",
    )
    p_batch.add_argument(
        "questions_file",
        type=Path,
        help="Path to file with one question per line",
    )
    p_batch.add_argument(
        "--out",
        required=True,
        help="JSONL output path (one JSON object per line)",
    )
    p_batch.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds between questions",
    )
    p_batch.add_argument(
        "--follow-up",
        action="store_true",
        help="Pass conversation_id from each response into the next call when present",
    )
    p_batch.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Optional per-query timeout seconds",
    )
    p_batch.set_defaults(func=run_ask_batch)

    args = parser.parse_args(argv)

    if args.cmd == "verify-export":
        return run_verify_export_cli(args.path, json_out=args.json)

    cfg = load_mcp_stdio_config()
    if args.mcp_command:
        cfg = McpStdioConfig(command=args.mcp_command.strip(), args=cfg.args)
    if args.mcp_args is not None:
        raw = args.mcp_args.strip()
        cfg = McpStdioConfig(command=cfg.command, args=raw.split() if raw else [])

    server_params = StdioServerParameters(command=cfg.command, args=cfg.args)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            func = args.func
            return await func(session, args)


def main_sync() -> None:
    raise SystemExit(asyncio.run(amain()))


if __name__ == "__main__":
    main_sync()
