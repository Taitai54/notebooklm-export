from notebooklm_export.mcp_util import parse_tool_json


def test_parse_tool_json_empty() -> None:
    out = parse_tool_json("")
    assert out["status"] == "error"


def test_parse_tool_json_invalid() -> None:
    out = parse_tool_json("not json")
    assert out["status"] == "error"
    assert "Invalid JSON" in out["message"]


def test_parse_tool_json_ok() -> None:
    out = parse_tool_json('{"status": "success", "notebooks": []}')
    assert out["status"] == "success"
