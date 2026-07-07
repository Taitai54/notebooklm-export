"""Parsing helpers and MCP stdio configuration for NotebookLM export."""

from __future__ import annotations

import json
import os
import re

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z",
    re.IGNORECASE,
)
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class McpStdioConfig:
    command: str
    args: list[str]


def load_mcp_stdio_config() -> McpStdioConfig:
    command = os.environ.get("NOTEBOOKLM_MCP_COMMAND", "notebooklm-mcp").strip()
    raw = os.environ.get("NOTEBOOKLM_MCP_ARGS", "").strip()
    args = raw.split() if raw else []
    return McpStdioConfig(command=command, args=args)


def first_text_block(result: Any) -> str:
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            return text
    return ""


def parse_tool_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        return {"status": "error", "message": "Empty MCP tool response"}
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON from MCP tool: {e}", "raw": text[:500]}


def slugify(name: str, max_len: int = 120) -> str:
    name = re.sub(r"[^\w\s.-]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name.strip())
    return (name or "untitled")[:max_len]


def extract_notebook_title_from_get(data: dict[str, Any]) -> str | None:
    """Human-readable notebook title from ``notebook_get``."""
    nb = data.get("notebook")
    if isinstance(nb, dict):
        title = nb.get("title")
        return title.strip() if isinstance(title, str) and title.strip() else None
    if not isinstance(nb, list) or not nb:
        return None
    inner = nb[0]
    if isinstance(inner, list) and inner and isinstance(inner[0], str):
        return inner[0]
    return None


def extract_sources_from_notebook_get(data: dict[str, Any]) -> list[tuple[str, str]]:
    """
    Parse ``notebook_get`` payload into (source_id, label) pairs.

    Supports the current MCP shape (``sources`` list of dicts) and the legacy
    nested array wire format used by older API responses.
    """
    sources = data.get("sources")
    if isinstance(sources, list):
        out: list[tuple[str, str]] = []
        for item in sources:
            if not isinstance(item, dict):
                continue
            sid = item.get("id") or item.get("source_id")
            if not isinstance(sid, str) or not sid:
                continue
            label = item.get("title") or item.get("label") or sid
            out.append((sid, label if isinstance(label, str) else sid))
        if out:
            return out

    nb = data.get("notebook")
    if not isinstance(nb, list) or not nb:
        return []
    inner = nb[0]
    if not isinstance(inner, list) or len(inner) < 2:
        return []
    sources_block = inner[1]
    if not isinstance(sources_block, list):
        return []

    out = []
    for item in sources_block:
        if not isinstance(item, list) or len(item) < 2:
            continue
        id_wrap, label = item[0], item[1]
        if isinstance(id_wrap, list) and id_wrap and isinstance(id_wrap[0], str):
            sid = id_wrap[0]
            lab = label if isinstance(label, str) else sid
            out.append((sid, lab))
    return out


def extract_source_details_from_notebook_get(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Like ``extract_sources_from_notebook_get`` but preserves extra fields when present."""
    sources = data.get("sources")
    if isinstance(sources, list) and sources and isinstance(sources[0], dict):
        out: list[dict[str, Any]] = []
        for item in sources:
            if not isinstance(item, dict):
                continue
            sid = item.get("id") or item.get("source_id")
            if not isinstance(sid, str) or not sid:
                continue
            row = {
                "id": sid,
                "title": item.get("title") or item.get("label") or sid,
            }
            if item.get("source_type"):
                row["source_type"] = item["source_type"]
            out.append(row)
        if out:
            return out

    return [
        {"id": sid, "title": label}
        for sid, label in extract_sources_from_notebook_get(data)
    ]


def parse_notebook_list(data: dict[str, Any]) -> list[dict[str, Any]]:
    if data.get("status") != "success":
        return []
    notebooks = data.get("notebooks")
    if not isinstance(notebooks, list):
        return []
    return [n for n in notebooks if isinstance(n, dict)]


def looks_like_notebook_uuid(ref: str) -> bool:
    return bool(_UUID_RE.match(ref.strip()))


def resolve_notebook_ref(notebooks: list[dict[str, Any]], ref: str) -> tuple[str | None, str]:
    """
    Map a user string to a notebook id.

    - If it looks like a UUID, return it as-is (caller should still verify via API).
    - Else match title: exact case-insensitive first, then unique substring.

    Returns (notebook_id_or_None, message). On success, message is a short log line;
    on failure, message is the error (multi-line allowed).
    """
    ref = ref.strip()
    if not ref:
        return None, "Empty notebook id or name."

    if looks_like_notebook_uuid(ref):
        return ref, ""

    needle = ref.casefold()

    exact: list[dict[str, Any]] = []
    for nb in notebooks:
        t = nb.get("title")
        if isinstance(t, str) and t.casefold().strip() == needle:
            exact.append(nb)

    if len(exact) == 1:
        nid = str(exact[0]["id"])
        title = exact[0].get("title", "")
        return nid, f'Resolved name (exact match) {title!r} -> {nid}'

    if len(exact) > 1:
        lines = [f'  {nb["id"]}\t{nb.get("title")}' for nb in exact]
        return None, "Multiple notebooks have that exact title; use the UUID:\n" + "\n".join(lines)

    subs: list[dict[str, Any]] = []
    for nb in notebooks:
        t = nb.get("title")
        if isinstance(t, str) and needle in t.casefold():
            subs.append(nb)

    if len(subs) == 1:
        nid = str(subs[0]["id"])
        title = subs[0].get("title", "")
        return nid, f'Resolved name (unique substring) {title!r} -> {nid}'

    if len(subs) > 1:
        lines = [f'  {nb["id"]}\t{nb.get("title")}' for nb in subs[:25]]
        more = f"\n  … and {len(subs) - 25} more" if len(subs) > 25 else ""
        return (
            None,
            "Multiple notebooks match that name as a substring; use a longer/sparser name or the UUID:\n"
            + "\n".join(lines)
            + more,
        )

    return (
        None,
        f'No notebook matched {ref!r}. Run "notebooklm-export list" to see titles and UUIDs.',
    )
