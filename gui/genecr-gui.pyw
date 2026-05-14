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


def detect_genecr_dir() -> Path | None:
    """Find genecr install across known host dirs."""
    home = Path.home()
    for host in (".gemini", ".claude", ".codex"):
        d = home / host / "skills" / "genecr"
        if (d / "pipeline.json").exists():
            return d
    return None


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
            messagebox.showerror(
                "未找到 genecr",
                "找不到 genecr 安裝。\n\n請先依手冊安裝：\n  https://github.com/ibalasite/genecr\n\n"
                "預期位置：\n  ~/.gemini/skills/genecr (Gemini)\n  ~/.claude/skills/genecr (Claude)\n  ~/.codex/skills/genecr  (Codex)"
            )

    # ─── UI layout ──────────────────────────────────────────────
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Top status bar
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        status_text = f"host: {self.host}  ｜  genecr: {self.genecr_dir or '未安裝'}"
        ttk.Label(top, text=status_text, foreground="#666").pack(side="left")

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
        self.outdir_var = tk.StringVar(value=str(Path.home() / "Desktop"))
        ttk.Entry(row2, textvariable=self.outdir_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(row2, text="瀏覽…", command=self._pick_outdir).pack(side="left")

        # Run button
        self.run_btn = ttk.Button(self, text="🚀 開始生成", command=self._on_run)
        self.run_btn.pack(pady=10)

        # Progress
        ttk.Label(self, text="進度：").pack(anchor="w", **pad)
        prog_frame = ttk.Frame(self, relief="sunken", borderwidth=1)
        prog_frame.pack(fill="x", padx=10, pady=(0, 6))
        self.step_labels = {}
        for s in STEPS:
            lbl = ttk.Label(prog_frame, text=f"⬜  {STEP_LABELS[s]}", font=("Microsoft JhengHei", 10))
            lbl.pack(anchor="w", padx=10, pady=2)
            self.step_labels[s] = lbl

        # Output log (small)
        self.log = tk.Text(self, height=4, wrap="word", state="disabled",
                            background="#f5f5f5", font=("Consolas", 9))
        self.log.pack(fill="x", padx=10, pady=(0, 6))

        # Results panel
        ttk.Label(self, text="產出（點選開啟）：").pack(anchor="w", **pad)
        self.results = ttk.Frame(self)
        self.results.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _clear_placeholder(self, _evt):
        if self._brief_placeholder:
            self.brief.delete("1.0", "end")
            self._brief_placeholder = False

    # ─── Auto-extract slug + name via Gemini ────────────────────
    def _on_extract(self):
        brief = self.brief.get("1.0", "end").strip()
        if not brief or self._brief_placeholder:
            messagebox.showwarning("缺少 brief", "請先輸入功能描述。")
            return
        self.extract_btn.configure(state="disabled", text="🪄 萃取中…")
        threading.Thread(target=self._extract_worker, args=(brief,), daemon=True).start()

    def _extract_worker(self, brief: str):
        # Pick CLI based on host. shutil.which resolves .cmd / .exe / .ps1 wrappers
        # on Windows (npm-installed clis are typically gemini.cmd).
        cli_map = {
            "gemini": (["gemini"], ["--skip-trust", "-p", " ", "--output-format", "text"]),
            "claude": (["claude"], ["-p", "--output-format", "text"]),
            "codex":  (["codex"],  ["exec", "--skip-git-repo-check"]),
        }
        if self.host not in cli_map:
            self.after(0, lambda: self._extract_done(None, "未知 host，無法呼叫 CLI"))
            return
        bin_name = cli_map[self.host][0][0]
        bin_path = shutil.which(bin_name)
        if not bin_path:
            self.after(0, lambda: self._extract_done(None,
                f"找不到 {bin_name} CLI。請確認已 `npm install -g @google/gemini-cli` 並重啟此視窗。"))
            return
        cli_cmd = [bin_path] + cli_map[self.host][1]

        prompt = (
            "從下面的功能需求描述中萃取兩個值，**只輸出 JSON**（無 markdown fence、無註解）：\n"
            "- slug: 英文小寫 kebab-case，反映核心功能，≤ 20 字元\n"
            "- name: 中文 2-6 字短名\n\n"
            "範例輸出：{\"slug\":\"daily-checkin\",\"name\":\"每日簽到\"}\n\n"
            "功能需求描述：\n"
            f"{brief}\n"
        )
        try:
            # On Windows, .cmd wrappers spawn cmd.exe which can flash; suppress.
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
            r = subprocess.run(
                cli_cmd, input=prompt, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=60,
                creationflags=creationflags,
            )
            out = (r.stdout or "").strip()
            # Strip code fences if any
            out = re.sub(r"^```(?:json)?\s*|\s*```$", "", out, flags=re.MULTILINE).strip()
            data = json.loads(out)
            self.after(0, lambda: self._extract_done(data, None))
        except subprocess.TimeoutExpired:
            self.after(0, lambda: self._extract_done(None, "CLI 超時（>60s）"))
        except json.JSONDecodeError as e:
            self.after(0, lambda: self._extract_done(None, f"AI 回傳非 JSON：{e}"))
        except FileNotFoundError:
            self.after(0, lambda: self._extract_done(None, f"找不到 {cli_cmd[0]} CLI，請確認已安裝"))
        except Exception as e:
            self.after(0, lambda: self._extract_done(None, str(e)))

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
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

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
        self.log.configure(state="normal"); self.log.delete("1.0", "end"); self.log.configure(state="disabled")
        self.run_btn.configure(state="disabled", text="生成中…")

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
            self.proc = subprocess.Popen(
                cmd, cwd=str(cwd),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                bufsize=1,
            )
            run_dir_pat = re.compile(r"Run:\s+(.+)")
            step_start = re.compile(r"^▶\s+(\S+):")
            step_done = re.compile(r"^\s+✓\s+(\S+):.*OK")
            render_done = re.compile(r"\[render\]\s+(\S+)\s+→")

            for line in self.proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                self.after(0, self._log, line)
                m = step_start.match(line)
                if m and m.group(1) in self.step_labels:
                    s = m.group(1)
                    self.after(0, lambda s=s: self.step_labels[s].configure(text=f"⏳  {STEP_LABELS[s]} 生成中…"))
                m = render_done.search(line)
                if m and m.group(1) in self.step_labels:
                    s = m.group(1)
                    self.after(0, lambda s=s: self.step_labels[s].configure(text=f"✅  {STEP_LABELS[s]}"))
                m = run_dir_pat.search(line)
                if m:
                    rd = m.group(1).strip()
                    # pipeline prints relative path; resolve against cwd
                    self.run_dir = (cwd / rd) if not Path(rd).is_absolute() else Path(rd)

            rc = self.proc.wait()
            if rc == 0:
                self.after(0, self._on_done, slug)
            else:
                self.after(0, self._log, f"❌ pipeline exited with code {rc}")
                self.after(0, lambda: self.run_btn.configure(state="normal", text="🚀 開始生成"))
        except Exception as e:
            self.after(0, self._log, f"❌ {e}")
            self.after(0, lambda: self.run_btn.configure(state="normal", text="🚀 開始生成"))

    def _on_done(self, slug: str):
        self.run_btn.configure(state="normal", text="🚀 開始生成")
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


if __name__ == "__main__":
    app = GenecrGUI()
    app.mainloop()
