"""Tkinter GUI: refresh notebook list, multi-select, export via existing CLI (subprocess)."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import tkinter as tk


def _gui_log_line_is_noise(line: str) -> bool:
    """
    notebooklm-mcp / FastMCP prints a large startup banner to the process log.
    It clutters the Tk log and may show box-drawing as literal \\u2584 escapes.
    Drop those lines; keep normal export messages and tracebacks.
    """
    if "FastMCP" in line or "gofastmcp" in line or "fastmcp.cloud" in line:
        return True
    if "Starting MCP server" in line and "stdio" in line:
        return True
    if "Update available:" in line and "fastmcp" in line.lower():
        return True
    if "Pin `fastmcp" in line or "Deploy free:" in line:
        return True
    if "server.py:" in line and "INFO" in line and "MCP server" in line:
        return True
    # Banner borders and logo rows (ASCII escapes or real block chars)
    if "\\u258" in line or "\\u2728" in line or "\\U0001f" in line:
        return True
    s = line.strip()
    if s.startswith("+") and s.rstrip().endswith("+") and "-" in s[:4]:
        return True
    if len(s) > 20 and s.startswith("|") and s.endswith("|"):
        mid = s[1:-1].strip()
        if not mid or mid.startswith("\\u") or "FastMCP" in mid or "notebooklm" in mid.lower():
            return True
    return False


def _parse_list_stdout(raw: str) -> dict:
    raw = raw.strip()
    if not raw:
        return {}
    i = raw.find("{")
    if i > 0:
        raw = raw[i:]
    return json.loads(raw)


def _run_list(max_results: int) -> tuple[list[dict], str | None]:
    cmd = [
        sys.executable,
        "-m",
        "notebooklm_export",
        "list",
        "--json",
        "--max-results",
        str(max_results),
    ]
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return [], "Timed out waiting for notebook list (MCP / network)."
    err = (p.stderr or "").strip()
    if p.returncode != 0:
        return [], (err or p.stdout or "list command failed")[:4000]
    try:
        data = _parse_list_stdout(p.stdout or "")
    except json.JSONDecodeError as e:
        return [], f"Could not parse list output as JSON: {e}\n\nFirst 500 chars:\n{(p.stdout or '')[:500]}"
    # CLI --json prints {"notebooks": [...]} (no "status" field)
    if data.get("status") is not None and data.get("status") != "success":
        return [], json.dumps(data, indent=2)[:4000]
    nbs = data.get("notebooks")
    if not isinstance(nbs, list):
        return [], "Unexpected list response: missing 'notebooks' array."
    return [x for x in nbs if isinstance(x, dict)], None


class NotebookExportGui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("NotebookLM export")
        self.root.minsize(720, 520)

        self._notebooks: list[dict] = []
        self._log_q: queue.Queue[str | None] = queue.Queue()
        self._busy = False

        default_out = Path.home() / "Documents" / "NotebookLM_exports"

        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Export folder:").pack(side=tk.LEFT)
        self.out_var = tk.StringVar(value=str(default_out))
        ttk.Entry(top, textvariable=self.out_var, width=56).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        ttk.Button(top, text="Browse…", command=self._browse_out).pack(side=tk.LEFT)

        opts = ttk.Frame(self.root, padding=(8, 0))
        opts.pack(fill=tk.X)
        self.var_summaries = tk.BooleanVar(value=False)
        self.var_sidecar_json = tk.BooleanVar(value=False)
        self.var_studio = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="AI summaries (.summary.md)", variable=self.var_summaries).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        ttk.Checkbutton(opts, text="Per-source .json files", variable=self.var_sidecar_json).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        ttk.Checkbutton(opts, text="Studio manifest", variable=self.var_studio).pack(side=tk.LEFT)

        mid = ttk.Frame(self.root, padding=8)
        mid.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(mid, text="Notebooks (Ctrl+click or Shift+click to select multiple)", padding=4)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(left)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox = tk.Listbox(
            left,
            selectmode=tk.EXTENDED,
            yscrollcommand=scroll.set,
            activestyle="dotbox",
            font=("Segoe UI", 10),
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.listbox.yview)

        right = ttk.Frame(mid, padding=(8, 0))
        right.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Button(right, text="Refresh list", command=self._refresh_async).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(right, text="Select all", command=self._select_all).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(right, text="Clear selection", command=self._clear_sel).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(right, text="Export selected", command=self._export_async).pack(fill=tk.X, pady=(12, 6))
        ttk.Button(right, text="Open export folder", command=self._open_out).pack(fill=tk.X, pady=(0, 6))

        log_fr = ttk.LabelFrame(self.root, text="Log", padding=4)
        log_fr.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        lscroll = ttk.Scrollbar(log_fr)
        lscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log = tk.Text(log_fr, height=10, wrap=tk.WORD, yscrollcommand=lscroll.set, font=("Consolas", 9))
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lscroll.config(command=self.log.yview)

        st = ttk.Frame(self.root, padding=(8, 0))
        st.pack(fill=tk.X, pady=(0, 6))
        self.status = ttk.Label(st, text="Load notebooks with “Refresh list”.")
        self.status.pack(side=tk.LEFT)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_log()

    def _browse_out(self) -> None:
        d = filedialog.askdirectory(initialdir=self.out_var.get() or str(Path.home()))
        if d:
            self.out_var.set(d)

    def _open_out(self) -> None:
        p = Path(self.out_var.get().strip() or ".")
        p.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(p)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(p)], check=False)
            else:
                subprocess.run(["xdg-open", str(p)], check=False)
        except OSError as e:
            messagebox.showerror("Open folder", str(e))

    def _log(self, s: str) -> None:
        self.log.insert(tk.END, s)
        self.log.see(tk.END)

    def _poll_log(self) -> None:
        try:
            while True:
                msg = self._log_q.get_nowait()
                if msg is None:
                    break
                self._log(msg)
        except queue.Empty:
            pass
        self.root.after(120, self._poll_log)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.status.config(text="Working…" if busy else "Ready.")

    def _refresh_async(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        self._log("\n--- Refreshing notebook list… ---\n")

        def work() -> None:
            nbs, err = _run_list(500)
            self.root.after(0, lambda: self._on_list_done(nbs, err))

        threading.Thread(target=work, daemon=True).start()

    def _on_list_done(self, nbs: list[dict], err: str | None) -> None:
        self._set_busy(False)
        if err:
            self._log(err + "\n")
            messagebox.showerror("Refresh failed", err[:1500])
            return
        self._notebooks = nbs
        self.listbox.delete(0, tk.END)
        for nb in nbs:
            tid = str(nb.get("id", ""))
            title = str(nb.get("title", "(no title)"))
            sc = nb.get("source_count", "?")
            self.listbox.insert(tk.END, f"{title}  —  {sc} sources  —  {tid[:8]}…")
        self._log(f"Loaded {len(nbs)} notebook(s).\n")

    def _select_all(self) -> None:
        if self.listbox.size() > 0:
            self.listbox.select_set(0, tk.END)

    def _clear_sel(self) -> None:
        self.listbox.selection_clear(0, tk.END)

    def _selected_indices(self) -> list[int]:
        return list(self.listbox.curselection())

    def _export_async(self) -> None:
        if self._busy:
            return
        idxs = self._selected_indices()
        if not idxs:
            messagebox.showinfo("Export", "Select one or more notebooks first.")
            return
        out = self.out_var.get().strip()
        if not out:
            messagebox.showerror("Export", "Choose an export folder.")
            return
        Path(out).mkdir(parents=True, exist_ok=True)

        items = [self._notebooks[i] for i in idxs if 0 <= i < len(self._notebooks)]
        if not items:
            messagebox.showerror("Export", "Selection does not match loaded list. Click Refresh.")
            return

        self._set_busy(True)
        self._log(f"\n--- Exporting {len(items)} notebook(s) to {out} ---\n")

        def work() -> None:
            try:
                for nb in items:
                    nb_id = str(nb.get("id", ""))
                    title = str(nb.get("title", nb_id))
                    if not nb_id:
                        self._log_q.put("[skip] missing id\n")
                        continue
                    self._log_q.put(f"\n>>> Export: {title}\n")
                    cmd = [
                        sys.executable,
                        "-m",
                        "notebooklm_export",
                        "export",
                        nb_id,
                        "--out",
                        out,
                        "--delay",
                        "0.2",
                    ]
                    if self.var_summaries.get():
                        cmd.append("--summaries")
                    if self.var_sidecar_json.get():
                        cmd.append("--sidecar-json")
                    if self.var_studio.get():
                        cmd.append("--studio-manifest")
                    child_env = {
                        **os.environ,
                        "PYTHONUNBUFFERED": "1",
                        "PYTHONIOENCODING": "utf-8",
                        "PYTHONUTF8": "1",
                        "NO_COLOR": "1",
                    }
                    try:
                        proc = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            bufsize=1,
                            env=child_env,
                        )
                        assert proc.stdout is not None
                        for line in proc.stdout:
                            if not _gui_log_line_is_noise(line):
                                self._log_q.put(line)
                        code = proc.wait(timeout=3600)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        self._log_q.put("[error] export timed out\n")
                        continue
                    except Exception as e:
                        self._log_q.put(f"[error] {e}\n")
                        continue
                    if code != 0:
                        self._log_q.put(f"[warning] exit code {code}\n")
            finally:
                self._log_q.put(None)
                self.root.after(0, lambda: self._export_finished())

        threading.Thread(target=work, daemon=True).start()

    def _export_finished(self) -> None:
        self._set_busy(False)
        self._log("\n--- Batch finished ---\n")
        self.status.config(text="Batch export finished — see log above.")

    def _on_close(self) -> None:
        if self._busy:
            if not messagebox.askyesno("Quit", "Export still running. Quit anyway?"):
                return
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    NotebookExportGui().run()


if __name__ == "__main__":
    main()
