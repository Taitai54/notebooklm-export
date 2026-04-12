from notebooklm_export.gui import _gui_log_line_is_noise


def test_keeps_export_line() -> None:
    assert not _gui_log_line_is_noise("Exported 3/3 sources to C:\\out\\December_a46a2146\n")


def test_drops_fastmcp_brand() -> None:
    assert _gui_log_line_is_noise("                               FastMCP 2.14.4                                \n")


def test_drops_unicode_escape_banner_chunk() -> None:
    assert _gui_log_line_is_noise("|                        \\u2584\\u2580\\u2580 \\u2584\\u2580\\u2588 \\u2588\\u2580\\u2580 \\u2580\\u2588\\u2580\n")


def test_drops_box_border() -> None:
    assert _gui_log_line_is_noise("+-----------------------------------------------------------------------------+\n")
