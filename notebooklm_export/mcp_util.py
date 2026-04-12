"""Parsing helpers and MCP stdio configuration for NotebookLM export."""

from __future__ import annotations

import json
import os
import re
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
        return {}
    return json.loads(text)


def slugify(name: str, max_len: int = 120) -> str:
    name = re.sub(r"[^\w\s.-]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name.strip())
    return (name or "untitled")[:max_len]


def extract_notebook_title_from_get(data: dict[str, Any]) -> str | None:
    """First element of the nested `notebook` array is the human title."""
    nb = data.get("notebook")
    if not isinstance(nb, list) or not nb:
        return None
    inner = nb[0]
    if isinstance(inner, list) and inner and isinstance(inner[0], str):
        return inner[0]
    return None


def extract_sources_from_notebook_get(data: dict[str, Any]) -> list[tuple[str, str]]:
    """
    Parse `notebook_get` payload: each source is
    [ [<source_uuid>], "filename_or_title", ... ].
    """
    nb = data.get("notebook")
    if not isinstance(nb, list) or not nb:
        return []
    inner = nb[0]
    if not isinstance(inner, list) or len(inner) < 2:
        return []
    sources_block = inner[1]
    if not isinstance(sources_block, list):
        return []

    out: list[tuple[str, str]] = []
    for item in sources_block:
        if not isinstance(item, list) or len(item) < 2:
            continue
        id_wrap, label = item[0], item[1]
        if isinstance(id_wrap, list) and id_wrap and isinstance(id_wrap[0], str):
            sid = id_wrap[0]
            lab = label if isinstance(label, str) else sid
            out.append((sid, lab))
    return out


def parse_notebook_list(data: dict[str, Any]) -> list[dict[str, Any]]:
    if data.get("status") != "success":
        return []
    notebooks = data.get("notebooks")
    if not isinstance(notebooks, list):
        return []
    return [n for n in notebooks if isinstance(n, dict)]
