"""
genecr-gui — Windows-friendly GUI wrapper for genecr pipeline.

Single-file tkinter app. Drives ~/.gemini/skills/genecr/tools/bin/pipeline.py
via subprocess and shows live progress. Designed for non-CLI users.

Run:
    pythonw genecr-gui.pyw
or just double-click the .pyw file.
"""

import os
import re
import sys
import json
import shutil
import threading
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

GENECR_REPO_URL = "https://github.com/ibalasite/genecr.git"

APP_TITLE = "genecr — iGaming 文件產生器"
STEPS = ["spec-basic", "spec-advanced", "assets", "bdd", "scrum", "prototype", "docs"]
STEP_LABELS = {
    "spec-basic": "📋 企畫版",
    "spec-advanced": "⚙️ 技術版",
    "assets": "🎨 資源清單",
    "bdd": "🧪 BDD 測試",
    "scrum": "📌 SCRUM 故事卡",
    "prototype": "🎮 互動原型",
    "docs": "🌐 整合文件",
}


HOST_DIRS = {
    "gemini": ".gemini",
    "claude": ".claude",
    "codex":  ".codex",
}


def list_installed_hosts() -> list[str]:
    """Return host names where genecr is installed (in preferred order)."""
    home = Path.home()
    return [h for h, d in HOST_DIRS.items()
            if (home / d / "skills" / "genecr" / "pipeline.json").exists()]


def host_to_dir(host: str) -> Path | None:
    home = Path.home()
    d = HOST_DIRS.get(host)
    if not d:
        return None
    p = home / d / "skills" / "genecr"
    return p if (p / "pipeline.json").exists() else None


def detect_genecr_dir() -> Path | None:
    """Find genecr install across known host dirs (first match)."""
    hosts = list_installed_hosts()
    return host_to_dir(hosts[0]) if hosts else None


def detect_pipeline_json(genecr_dir: Path, host: str) -> Path:
    """Pick host-specific pipeline.json if present."""
    if host == "gemini" and (genecr_dir / "pipeline-gemini.json").exists():
        return genecr_dir / "pipeline-gemini.json"
    return genecr_dir / "pipeline.json"


def detect_host(genecr_dir: Path) -> str:
    s = str(genecr_dir).replace("\\", "/")
    for h in ("gemini", "claude", "codex"):
        if f"/.{h}/" in s:
            return h
    return "unknown"


def default_outdir() -> Path:
    """Pick a sensible default output dir (OneDrive Desktop / Desktop / Documents / home)."""
    home = Path.home()
    for cand in (home / "OneDrive" / "桌面",
                 home / "OneDrive" / "Desktop",
                 home / "Desktop",
                 home / "Documents",
                 home):
        if cand.exists():
            return cand
    return home


def find_python() -> str:
    """Find a real Python 3 (skip Microsoft Store stub)."""
    for cand in ("python3", "python"):
        try:
            r = subprocess.run([cand, "--version"], capture_output=True, text=True, timeout=3)
            if r.returncode == 0 and r.stdout.startswith("Python 3"):
                return cand
        except Exception:
            continue
    return sys.executable  # fall back to current interpreter


# ─── Pure helpers (no UI; testable headless) ────────────────────
CLI_MAP = {
    "gemini": (["gemini"], ["--skip-trust", "-p", " ", "--output-format", "text"]),
    "claude": (["claude"], ["-p", "--output-format", "text"]),
    "codex":  (["codex"],  ["exec", "--skip-git-repo-check"]),
}

EXTRACT_PROMPT = (
    "從下面的功能需求描述中萃取兩個值，**只輸出 JSON**（無 markdown fence、無註解）：\n"
    "- slug: 英文小寫 kebab-case，反映核心功能，≤ 20 字元\n"
    "- name: 中文 2-6 字短名\n\n"
    "範例輸出：{\"slug\":\"daily-checkin\",\"name\":\"每日簽到\"}\n\n"
    "功能需求描述：\n"
    "{brief}\n"
)


def extract_slug_name(brief: str, host: str, timeout: int = 60) -> tuple[dict | None, str | None]:
    """Call host CLI to extract {slug, name} from brief. Returns (data, error)."""
    if host not in CLI_MAP:
        return None, f"未知 host: {host}"
    bin_name = CLI_MAP[host][0][0]
    bin_path = shutil.which(bin_name)
    if not bin_path:
        return None, f"找不到 {bin_name} CLI"
    cli_cmd = [bin_path] + CLI_MAP[host][1]
    prompt = EXTRACT_PROMPT.replace("{brief}", brief)
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    try:
        r = subprocess.run(
            cli_cmd, input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=creationflags,
        )
        out = (r.stdout or "").strip()
        out = re.sub(r"^```(?:json)?\s*|\s*```$", "", out, flags=re.MULTILINE).strip()
        return json.loads(out), None
    except subprocess.TimeoutExpired:
        return None, f"CLI 超時（>{timeout}s）"
    except json.JSONDecodeError as e:
        return None, f"AI 回傳非 JSON：{e}"
    except Exception as e:
        return None, str(e)


def parse_pipeline_line(line: str) -> tuple[str, str] | None:
    """Parse one pipeline.py stdout line. Returns (event, step) or None.
    event ∈ {'start', 'done', 'render_done', 'run_dir'}.
    """
    m = re.match(r"^▶\s+(\S+):", line)
    if m:
        return ("start", m.group(1))
    m = re.match(r"^\s+✓\s+(\S+):.*OK", line)
    if m:
        return ("done", m.group(1))
    m = re.search(r"\[render\]\s+(\S+)\s+→", line)
    if m:
        return ("render_done", m.group(1))
    m = re.search(r"Run:\s+(.+)", line)
    if m:
        return ("run_dir", m.group(1).strip())
    return None


# ─── Prerequisite detection (for first-run install wizard) ──────
def check_prereq(name: str) -> bool:
    """Check if a prerequisite is available."""
    if name == "node":   return shutil.which("node") is not None
    if name == "git":    return shutil.which("git")  is not None
    if name == "python": return True  # we're running on python
    if name == "winget": return shutil.which("winget") is not None
    if name == "gemini": return shutil.which("gemini") is not None
    if name == "genecr": return (Path.home() / ".gemini" / "skills" / "genecr" / "pipeline.json").exists()
    return False


PREREQ_INSTALL = {
    "node":   ["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS", "--accept-package-agreements", "--accept-source-agreements"],
    "git":    ["winget", "install", "-e", "--id", "Git.Git",          "--accept-package-agreements", "--accept-source-agreements"],
    "gemini": ["npm",    "install", "-g", "@google/gemini-cli"],
}

PREREQ_LABELS = {
    "node":   "Node.js (npm 用)",
    "git":    "Git",
    "gemini": "Gemini CLI",
    "genecr": "genecr (本工具核心)",
}


class GenecrGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x720")
        self.minsize(640, 600)

        self.genecr_dir = detect_genecr_dir()
        self.host = detect_host(self.genecr_dir) if self.genecr_dir else "unknown"
        self.python = find_python()
        self.proc = None
        self.run_dir: Path | None = None

        self._build_ui()

        if not self.genecr_dir:
            self.after(200, self._open_install_wizard)

    # ─── UI layout ──────────────────────────────────────────────
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Top status bar — host picker (Combobox only when 2+ installed)
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="host：").pack(side="left")
        installed = list_installed_hosts()
        default_host = self.host if self.host in installed else (installed[0] if installed else "unknown")
        self.host_var = tk.StringVar(value=default_host)
        if len(installed) >= 2:
            self.host_combo = ttk.Combobox(top, textvariable=self.host_var, width=10,
                                            values=installed, state="readonly")
            self.host_combo.pack(side="left")
            self.host_combo.bind("<<ComboboxSelected>>", self._on_host_change)
        else:
            ttk.Label(top, text=default_host, font=("", 10, "bold")).pack(side="left")
        self.path_label = ttk.Label(top, text="", foreground="#666")
        self.path_label.pack(side="left", padx=(10, 0))
        self._refresh_path_label()

        # Brief input
        ttk.Label(self, text="功能描述（brief）— 越詳細越好：").pack(anchor="w", **pad)
        self.brief = tk.Text(self, height=8, wrap="word", font=("Microsoft JhengHei", 10))
        self.brief.pack(fill="both", expand=False, padx=10, pady=(0, 6))
        self.brief.insert("1.0",
            "範例：老玩家儲值滿 1000 送刮刮券，遊戲中也會掉，最高 5000 倍，\n"
            "未中獎有幸運代號每週開獎，不能讓代理商損失"
        )
        # Click-to-clear placeholder behavior
        self._brief_placeholder = True
        self.brief.bind("<FocusIn>", self._clear_placeholder)

        # slug + name (with auto-extract button)
        row = ttk.Frame(self)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="英文 slug：").pack(side="left")
        self.slug_var = tk.StringVar(value="my-feature")
        ttk.Entry(row, textvariable=self.slug_var, width=22).pack(side="left", padx=(0, 12))
        ttk.Label(row, text="中文名稱：").pack(side="left")
        self.name_var = tk.StringVar(value="我的功能")
        ttk.Entry(row, textvariable=self.name_var, width=14).pack(side="left", padx=(0, 8))
        self.extract_btn = ttk.Button(row, text="🪄 從描述自動萃取", command=self._on_extract)
        self.extract_btn.pack(side="left")

        # output dir
        row2 = ttk.Frame(self)
        row2.pack(fill="x", **pad)
        ttk.Label(row2, text="輸出位置：").pack(side="left")
        self.outdir_var = tk.StringVar(value=str(default_outdir()))
        ttk.Entry(row2, textvariable=self.outdir_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(row2, text="瀏覽…", command=self._pick_outdir).pack(side="left")

        # Run / Cancel buttons
        btn_row = ttk.Frame(self)
        btn_row.pack(pady=10)
        self.run_btn = ttk.Button(btn_row, text="🚀 開始生成", command=self._on_run)
        self.run_btn.pack(side="left", padx=4)
        self.cancel_btn = ttk.Button(btn_row, text="✋ 取消", command=self._on_cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=4)

        # Progress
        ttk.Label(self, text="進度：").pack(anchor="w", **pad)
        prog_frame = ttk.Frame(self, relief="sunken", borderwidth=1)
        prog_frame.pack(fill="x", padx=10, pady=(0, 6))
        self.step_labels = {}
        for s in STEPS:
            lbl = ttk.Label(prog_frame, text=f"⬜  {STEP_LABELS[s]}", font=("Microsoft JhengHei", 10))
            lbl.pack(anchor="w", padx=10, pady=2)
            self.step_labels[s] = lbl

        # Progress bar
        prog_row = ttk.Frame(self)
        prog_row.pack(fill="x", padx=10, pady=(0, 6))
        self.progress = ttk.Progressbar(prog_row, mode="determinate", maximum=len(STEPS) * 2)
        self.progress.pack(side="left", fill="x", expand=True)
        self.detail_btn = ttk.Button(prog_row, text="📋 複製 log", width=10, command=self._copy_log)
        self.detail_btn.pack(side="left", padx=(6, 0))

        # Inline log panel (always visible, like wizard)
        log_frame = ttk.LabelFrame(self, text="執行進度")
        log_frame.pack(fill="x", padx=10, pady=(0, 6))
        self.log_text = tk.Text(log_frame, height=6, font=("Consolas", 9),
                                 state="disabled", background="#1e1e1e", foreground="#ddd")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

        # Internal log buffer (mirrors log_text contents)
        self._log_buffer: list[str] = []

        # Results panel
        ttk.Label(self, text="產出（點選開啟）：").pack(anchor="w", **pad)
        self.results = ttk.Frame(self)
        self.results.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _clear_placeholder(self, _evt):
        if self._brief_placeholder:
            self.brief.delete("1.0", "end")
            self._brief_placeholder = False

    def _on_host_change(self, _evt=None):
        self.host = self.host_var.get()
        self.genecr_dir = host_to_dir(self.host)
        self._refresh_path_label()

    def _refresh_path_label(self):
        gd = self.genecr_dir
        self.path_label.configure(text=f"｜  {gd}" if gd else "｜  未偵測到 genecr")

    # ─── Auto-extract slug + name via Gemini ────────────────────
    def _on_extract(self):
        brief = self.brief.get("1.0", "end").strip()
        if not brief or self._brief_placeholder:
            messagebox.showwarning("缺少 brief", "請先輸入功能描述。")
            return
        self.extract_btn.configure(state="disabled", text="🪄 萃取中…")
        threading.Thread(target=self._extract_worker, args=(brief,), daemon=True).start()

    def _extract_worker(self, brief: str):
        data, err = extract_slug_name(brief, self.host)
        self.after(0, lambda: self._extract_done(data, err))

    def _extract_done(self, data, err):
        self.extract_btn.configure(state="normal", text="🪄 從描述自動萃取")
        if err:
            messagebox.showerror("萃取失敗", err)
            return
        slug = (data.get("slug") or "").strip()
        name = (data.get("name") or "").strip()
        if slug:
            self.slug_var.set(slug)
        if name:
            self.name_var.set(name)
        self._log(f"✓ 已萃取：slug={slug}  name={name}")

    def _pick_outdir(self):
        d = filedialog.askdirectory(initialdir=self.outdir_var.get())
        if d:
            self.outdir_var.set(d)

    def _log(self, msg: str):
        self._log_buffer.append(msg)
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _copy_log(self):
        self.clipboard_clear()
        self.clipboard_append("\n".join(self._log_buffer))
        messagebox.showinfo("已複製", "log 已複製到剪貼簿。")

    def _show_log(self):
        # Kept for error dialog "看詳細 log" button — show in larger window
        win = tk.Toplevel(self)
        win.title("完整 log")
        win.geometry("760x520")
        txt = tk.Text(win, wrap="none", font=("Consolas", 9))
        ys = ttk.Scrollbar(win, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        full = "\n".join(self._log_buffer)
        txt.insert("1.0", full or "(尚無內容)")
        txt.configure(state="disabled")
        ttk.Button(win, text="關閉", command=win.destroy).pack(pady=4)

    # ─── Run pipeline ───────────────────────────────────────────
    def _on_run(self):
        if not self.genecr_dir:
            messagebox.showerror("錯誤", "未找到 genecr 安裝。")
            return
        brief = self.brief.get("1.0", "end").strip()
        if not brief or self._brief_placeholder:
            messagebox.showwarning("缺少 brief", "請輸入功能描述。")
            return
        slug = self.slug_var.get().strip() or "my-feature"
        name = self.name_var.get().strip() or "我的功能"
        outdir = Path(self.outdir_var.get()).expanduser()
        if not outdir.exists():
            messagebox.showerror("錯誤", f"輸出位置不存在：{outdir}")
            return

        # Reset progress UI
        for s in STEPS:
            self.step_labels[s].configure(text=f"⬜  {STEP_LABELS[s]}")
        for w in self.results.winfo_children():
            w.destroy()
        self._log_buffer.clear()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.progress.configure(value=0)
        self.run_btn.configure(state="disabled", text="生成中…")
        self.cancel_btn.configure(state="normal")

        pipeline_json = detect_pipeline_json(self.genecr_dir, self.host)
        pipeline_py = self.genecr_dir / "tools" / "bin" / "pipeline.py"

        cmd = [
            self.python, str(pipeline_py), str(pipeline_json),
            "--new", "--slug", slug, "--name", name, brief,
        ]
        # Run from outdir so output/ goes there
        threading.Thread(target=self._run_pipeline, args=(cmd, outdir, slug), daemon=True).start()

    def _run_pipeline(self, cmd: list[str], cwd: Path, slug: str):
        try:
            self.after(0, self._log, f"$ cd {cwd}")
            self.after(0, self._log, "$ " + " ".join(f'"{c}"' if " " in c else c for c in cmd[:6]) + " ...")
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
            self.proc = subprocess.Popen(
                cmd, cwd=str(cwd), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                bufsize=1, creationflags=creationflags,
            )

            for line in self.proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                self.after(0, self._log, line)
                evt = parse_pipeline_line(line)
                if evt:
                    kind, val = evt
                    if kind == "start" and val in self.step_labels:
                        self.after(0, lambda s=val: self.step_labels[s].configure(text=f"⏳  {STEP_LABELS[s]} 生成中…"))
                        self.after(0, self._bump_progress, 1)
                    elif kind == "render_done" and val in self.step_labels:
                        self.after(0, lambda s=val: self.step_labels[s].configure(text=f"✅  {STEP_LABELS[s]}"))
                        self.after(0, self._bump_progress, 1)
                    elif kind == "run_dir":
                        self.run_dir = (cwd / val) if not Path(val).is_absolute() else Path(val)

            rc = self.proc.wait()
            if rc == 0:
                self.after(0, self._on_done, slug)
            else:
                self.after(0, self._log, f"❌ pipeline exited with code {rc}")
                self.after(0, self._on_error, f"產生過程出錯（exit code {rc}）")
        except Exception as e:
            self.after(0, self._log, f"❌ {e}")
            self.after(0, self._on_error, str(e))

    def _bump_progress(self, n: int = 1):
        self.progress.configure(value=min(self.progress["value"] + n, len(STEPS) * 2))

    def _on_cancel(self):
        if not self.proc:
            return
        try:
            # On Windows, terminate kills the whole process tree (mostly)
            self.proc.terminate()
            self._log("⚠ 使用者取消")
        except Exception as e:
            self._log(f"取消失敗：{e}")
        finally:
            self.cancel_btn.configure(state="disabled")
            self.run_btn.configure(state="normal", text="🚀 開始生成")

    def _on_error(self, summary: str):
        self.run_btn.configure(state="normal", text="🚀 開始生成")
        self.cancel_btn.configure(state="disabled")
        # Custom error dialog with copy button
        win = tk.Toplevel(self)
        win.title("發生錯誤")
        win.geometry("520x260")
        ttk.Label(win, text="⚠ " + summary, foreground="#c00",
                  font=("Microsoft JhengHei", 11)).pack(pady=(20, 6), padx=20, anchor="w")
        ttk.Label(win, text="可以點下方按鈕看完整訊息或複製給工程師。",
                  foreground="#555").pack(padx=20, anchor="w")
        bar = ttk.Frame(win)
        bar.pack(fill="x", padx=20, pady=20)
        ttk.Button(bar, text="📋 複製錯誤訊息", command=lambda: (
            self.clipboard_clear(),
            self.clipboard_append("\n".join(self._log_buffer)),
            messagebox.showinfo("已複製", "已複製到剪貼簿。", parent=win)
        )).pack(side="left")
        ttk.Button(bar, text="📄 看詳細 log", command=self._show_log).pack(side="left", padx=8)
        ttk.Button(bar, text="關閉", command=win.destroy).pack(side="right")

    def _on_done(self, slug: str):
        self.run_btn.configure(state="normal", text="🚀 開始生成")
        self.cancel_btn.configure(state="disabled")
        if not self.run_dir or not self.run_dir.exists():
            self._log("⚠ 找不到 run 目錄")
            return
        # List the 7 deliverables
        files = sorted([
            p for p in self.run_dir.iterdir()
            if p.suffix in (".md", ".html") and not p.name.endswith("combined.prompt.md")
        ])
        # Show docs.html first as primary entry
        files.sort(key=lambda p: 0 if p.name.endswith("docs.html") else 1)
        for p in files:
            self._add_result_row(p)

    def _add_result_row(self, path: Path):
        row = ttk.Frame(self.results)
        row.pack(fill="x", pady=2)
        is_html = path.suffix == ".html"
        is_main = path.name.endswith("docs.html")
        icon = "🌐" if is_html else "📄"
        label_text = f"{icon}  {path.name}"
        if is_main:
            label_text += "  ⭐"
        ttk.Label(row, text=label_text, font=("Microsoft JhengHei", 10)).pack(side="left")
        ttk.Button(row, text="開啟", width=8,
                   command=lambda p=path: self._open_file(p)).pack(side="right", padx=2)
        ttk.Button(row, text="資料夾", width=8,
                   command=lambda p=path: self._open_folder(p)).pack(side="right", padx=2)

    def _open_file(self, path: Path):
        try:
            if path.suffix == ".html":
                webbrowser.open(path.as_uri())
            else:
                os.startfile(str(path))
        except Exception as e:
            messagebox.showerror("無法開啟", str(e))

    def _open_folder(self, path: Path):
        try:
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        except Exception as e:
            messagebox.showerror("無法開啟資料夾", str(e))

    # ─── First-run install wizard (auto-install all) ────────────
    def _open_install_wizard(self):
        win = tk.Toplevel(self)
        win.title("首次安裝精靈")
        win.geometry("560x500")
        win.transient(self)
        win.grab_set()

        ttk.Label(win, text="歡迎使用 genecr！", font=("Microsoft JhengHei", 13, "bold")).pack(pady=(16, 4))
        ttk.Label(win, text="按下方按鈕，會自動把缺少的東西全部裝好。",
                  foreground="#555").pack()
        ttk.Label(win, text="（途中可能彈出 Windows UAC 同意框，請點「是」）",
                  foreground="#888", font=("Microsoft JhengHei", 9)).pack()

        list_frame = ttk.Frame(win)
        list_frame.pack(fill="both", expand=True, padx=20, pady=14)

        prereqs = ["node", "git", "gemini", "genecr"]
        status_labels: dict[str, ttk.Label] = {}

        def set_status(name, icon, suffix=""):
            status_labels[name].configure(text=f"{icon}  {PREREQ_LABELS[name]}{suffix}")

        def refresh_status():
            for name in prereqs:
                set_status(name, "✅" if check_prereq(name) else "❌")

        for name in prereqs:
            lbl = ttk.Label(list_frame, text=f"⬜  {PREREQ_LABELS[name]}",
                             font=("Microsoft JhengHei", 11), anchor="w")
            lbl.pack(fill="x", pady=4)
            status_labels[name] = lbl

        # Live log area (shown during auto-install)
        log_frame = ttk.LabelFrame(win, text="安裝進度")
        log_frame.pack(fill="both", expand=False, padx=20, pady=(0, 8))
        log_text = tk.Text(log_frame, height=6, font=("Consolas", 9), state="disabled")
        log_text.pack(fill="both", expand=True, padx=4, pady=4)

        def log(msg):
            log_text.configure(state="normal")
            log_text.insert("end", msg + "\n")
            log_text.see("end")
            log_text.configure(state="disabled")

        # Buttons row
        bar = ttk.Frame(win)
        bar.pack(fill="x", padx=20, pady=10)
        start_btn = ttk.Button(bar, text="🔧 開始自動安裝")
        start_btn.pack(side="left")
        login_btn = ttk.Button(bar, text="🔑 登入 Gemini", state="disabled",
                                command=lambda: self._wizard_login_gemini(win))
        login_btn.pack(side="left", padx=8)
        finish_btn = ttk.Button(bar, text="✅ 完成（重啟）", state="disabled",
                                 command=lambda: (win.destroy(), self._restart()))
        finish_btn.pack(side="right")

        def run_step(name) -> bool:
            cmd = PREREQ_INSTALL.get(name)
            if name == "genecr":
                target = Path.home() / ".gemini" / "skills" / "genecr"
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    if not self._wizard_run_blocking(["git", "clone", GENECR_REPO_URL, str(target)], log):
                        return False
                if sys.platform == "win32" and (target / "setup.ps1").exists():
                    cmd2 = ["powershell", "-NoProfile", "-File", str(target / "setup.ps1"), "install", "gemini"]
                else:
                    cmd2 = ["bash", str(target / "setup"), "install", "gemini"]
                return self._wizard_run_blocking(cmd2, log)
            if cmd is None:
                return True
            if cmd[0] == "winget" and not check_prereq("winget"):
                log(f"❌ 沒有 winget，無法自動裝 {name}。請手動安裝。")
                return False
            return self._wizard_run_blocking(cmd, log)

        def auto_install():
            start_btn.configure(state="disabled", text="安裝中…")
            for name in prereqs:
                if check_prereq(name):
                    set_status(name, "✅")
                    log(f"✓ {PREREQ_LABELS[name]} 已安裝，跳過")
                    continue
                set_status(name, "⏳", "  安裝中…")
                log(f"\n=== 安裝 {PREREQ_LABELS[name]} ===")
                ok = run_step(name)
                if ok and check_prereq(name):
                    set_status(name, "✅")
                    log(f"✓ {PREREQ_LABELS[name]} 完成")
                else:
                    set_status(name, "❌", "  安裝失敗")
                    log(f"✗ {PREREQ_LABELS[name]} 失敗，請看上面訊息")
                    start_btn.configure(state="normal", text="🔁 重試")
                    return
            # All installed → enable login button
            log("\n✅ 所有套件已安裝。請按「登入 Gemini」完成 Google 帳號授權。")
            start_btn.configure(text="✅ 安裝完成")
            login_btn.configure(state="normal")
            # Allow finish (login is manual but can skip if already logged in)
            finish_btn.configure(state="normal")

        start_btn.configure(command=lambda: threading.Thread(target=auto_install, daemon=True).start())

        refresh_status()
        # Auto-trigger if anything missing? — keep manual click so user sees what's about to happen
        # User can click 🔧 once.

    def _wizard_run_blocking(self, cmd: list[str], log) -> bool:
        """Run cmd synchronously, stream lines to log(), return True on rc=0."""
        try:
            resolved = shutil.which(cmd[0]) or cmd[0]
            full = [resolved] + cmd[1:]
            self.after(0, log, f"$ {' '.join(cmd)}")
            proc = subprocess.Popen(
                full, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
            for line in proc.stdout:
                self.after(0, log, line.rstrip())
            rc = proc.wait()
            return rc == 0
        except Exception as e:
            self.after(0, log, f"❌ {e}")
            return False

    def _wizard_login_gemini(self, parent):
        # Open Gemini interactively in a new console window for OAuth login.
        try:
            if sys.platform == "win32":
                # 'start' detaches into a new visible cmd window
                subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", "gemini"], shell=False)
            else:
                subprocess.Popen(["x-terminal-emulator", "-e", "gemini"])
            messagebox.showinfo("Gemini 登入",
                "已開啟新終端機。請在那邊完成 Google 登入後，回來按「🔄 重新檢測」。",
                parent=parent)
        except Exception as e:
            messagebox.showerror("無法開啟", str(e), parent=parent)

    def _restart(self):
        """Restart this app so the wizard's installs take effect."""
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            messagebox.showinfo("請手動重開", "安裝完成。請關閉並重新開啟視窗。", parent=self)
            self.destroy()


if __name__ == "__main__":
    app = GenecrGUI()
    app.mainloop()
