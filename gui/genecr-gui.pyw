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
GENECR_RELEASES_API = "https://api.github.com/repos/ibalasite/genecr/releases/latest"
GENECR_RELEASES_PAGE = "https://github.com/ibalasite/genecr/releases/latest"
APP_VERSION = "0.1.11"

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
    out = ""
    try:
        r = subprocess.run(
            cli_cmd, input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=creationflags,
        )
        out = (r.stdout or "").strip()
        if not out:
            stderr = (r.stderr or "").strip()
            # Don't guess the cause here — caller (_extract_done) classifies via stderr.
            return None, f"{host} CLI 回傳空字串。\n\nCLI stderr：\n{stderr[:500] if stderr else '(stderr 為空)'}"
        out = re.sub(r"^```(?:json)?\s*|\s*```$", "", out, flags=re.MULTILINE).strip()
        return json.loads(out), None
    except subprocess.TimeoutExpired:
        return None, f"CLI 超時（>{timeout}s）"
    except json.JSONDecodeError as e:
        return None, f"AI 回傳非 JSON：{e}\n\n原始內容前 300 字：\n{out[:300]}"
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
    if name == "python":
        # Check for SYSTEM python (not the PyInstaller-bundled one).
        # Subprocess needs a real python.exe to run pipeline.py / pip install.
        for cand in ("python3", "python"):
            path = shutil.which(cand)
            if not path: continue
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0  # type: ignore[attr-defined]
                r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=3, creationflags=creationflags)
                if r.returncode == 0 and r.stdout.startswith("Python 3"):
                    return True
            except Exception:
                continue
        return False
    if name == "winget": return shutil.which("winget") is not None
    if name == "gemini": return shutil.which("gemini") is not None
    if name == "genecr": return (Path.home() / ".gemini" / "skills" / "genecr" / "pipeline.json").exists()
    return False


# Multi-method install chain — try each in order, fall through on failure.
# Each method is a tuple:
#   ("winget",   [winget cmd args])           — try winget first (fastest if it works)
#   ("download", url, [silent install args])  — fall back to direct official download
#   ("npm",      [npm cmd args])              — npm install (no fallback for npm tools)
PREREQ_METHODS = {
    "python": [
        ("winget",   ["winget", "install", "-e", "--id", "Python.Python.3.13",
                       "--accept-package-agreements", "--accept-source-agreements"]),
        ("download", "https://www.python.org/ftp/python/3.13.1/python-3.13.1-amd64.exe",
                     ["/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0"]),
    ],
    "node": [
        ("winget",   ["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS",
                       "--accept-package-agreements", "--accept-source-agreements"]),
        ("download", "https://nodejs.org/dist/v22.11.0/node-v22.11.0-x64.msi",
                     ["/quiet", "/norestart", "ADDLOCAL=ALL"]),
    ],
    "git": [
        ("winget",   ["winget", "install", "-e", "--id", "Git.Git",
                       "--accept-package-agreements", "--accept-source-agreements"]),
        ("download", "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe",
                     ["/VERYSILENT", "/NORESTART", "/NOCANCEL", "/SP-",
                      "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"]),
    ],
    "gemini": [
        ("npm", ["npm", "install", "-g", "@google/gemini-cli"]),
    ],
    "claude": [
        ("npm", ["npm", "install", "-g", "@anthropic-ai/claude-code"]),
    ],
    "codex": [
        ("npm", ["npm", "install", "-g", "@openai/codex"]),
    ],
}

PREREQ_LABELS = {
    "python": "Python 3 (執行 pipeline 用)",
    "node":   "Node.js (npm 用)",
    "git":    "Git",
    "gemini": "Gemini CLI",
    "claude": "Claude Code CLI",
    "codex":  "Codex CLI",
    "genecr": "genecr (本工具核心)",
}

HOST_BIN = {"gemini": "gemini", "claude": "claude", "codex": "codex"}

# Local OAuth credential file paths (for zero-token login state check).
# Verified by listing actual ~/.gemini/, ~/.codex/, ~/.claude/ — these are
# the files each CLI creates after a successful login.
AUTH_FILES = {
    "gemini": [Path.home() / ".gemini" / "oauth_creds.json"],
    "claude": [Path.home() / ".claude" / ".credentials.json"],
    "codex":  [Path.home() / ".codex"  / "auth.json"],
}


def check_login_state(host: str) -> bool:
    """Return True if local OAuth credentials exist for the host. Zero token cost."""
    return any(p.exists() for p in AUTH_FILES.get(host, []))


def classify_call_failure(err_text: str) -> str:
    """Classify why an AI call failed by inspecting the error/stderr text.
    Returns one of: 'quota' / 'not_logged_in' / 'network' / 'unknown'.
    Does NOT make any AI calls — pure string analysis."""
    s = (err_text or "").lower()
    quota_kws = ("limit reached", "quota", "exceeded", "exhaust", "rate limit",
                 "resource exhausted", "restricting models", "too many requests",
                 "ratelimit", "429")
    auth_kws = ("auth", "login", "credential", "unauthor", "sign in", "401",
                "permission denied", "not authenticated")
    net_kws  = ("network", "timeout", "unreachable", "dns", "connect refused",
                "econnrefused", "etimedout", "enotfound", "getaddrinfo")
    if any(k in s for k in quota_kws): return "quota"
    if any(k in s for k in auth_kws):  return "not_logged_in"
    if any(k in s for k in net_kws):   return "network"
    return "unknown"


def host_cli_installed(host: str) -> bool:
    return shutil.which(HOST_BIN.get(host, "")) is not None


def host_genecr_installed(host: str) -> bool:
    d = HOST_DIRS.get(host)
    return bool(d and (Path.home() / d / "skills" / "genecr" / "pipeline.json").exists())


def deploy_genecr_python_native(host: str, log) -> bool:
    """Python-native deploy — replaces setup.ps1 / setup bash for locked-down
    Windows envs where PowerShell is blocked. Does:
      1. Copy {runtime}/skills/* → ~/.X/skills/
      2. pip install -r tools/renderer/requirements.txt
      3. Copy tools/renderer/*.py → tools/bin/
    Assumes git clone to {runtime} already done.
    """
    import shutil as sh
    home = Path.home()
    host_dir = HOST_DIRS.get(host)
    if not host_dir:
        log(f"❌ 未知 host: {host}")
        return False
    runtime = home / host_dir / "skills" / "genecr"
    skills_dst = home / host_dir / "skills"

    if not runtime.exists():
        log(f"❌ 找不到 runtime: {runtime}")
        return False

    # 1. Deploy skills
    skills_src = runtime / "skills"
    if skills_src.exists():
        log(f"[deploy] {skills_src} → {skills_dst}")
        skills_dst.mkdir(parents=True, exist_ok=True)
        for child in skills_src.iterdir():
            if not child.is_dir():
                continue
            dst = skills_dst / child.name
            if dst.exists():
                sh.rmtree(dst)
            sh.copytree(child, dst)
            log(f"  · {child.name}")

    # 2. Deploy tools — pip install + copy py files
    renderer = runtime / "tools" / "renderer"
    bin_dir = runtime / "tools" / "bin"
    if renderer.exists():
        bin_dir.mkdir(parents=True, exist_ok=True)
        req = renderer / "requirements.txt"
        if req.exists():
            log(f"[deploy] pip install -r {req}")
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0  # type: ignore[attr-defined]
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-q", "-r", str(req)],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    creationflags=creationflags,
                )
                if r.returncode != 0:
                    log(f"  ⚠ pip 失敗：{r.stderr[:200]}")
            except Exception as e:
                log(f"  ⚠ pip 例外：{e}")
        for fname in ("render.py", "pipeline.py", "orchestrate.py"):
            src = renderer / fname
            if src.exists():
                sh.copy2(src, bin_dir / fname)
                log(f"  · tools/bin/{fname}")

    log(f"✅ deploy 完成")
    return True


# ─── Login verification (zero token cost — local checks only) ───
# Status codes: "ok_locally" / "cli_missing" / "not_logged_in"
# NOTE: cannot detect "quota" — that's only knowable when the user
# actually runs work and the AI returns an error. See _extract_done()
# stderr classification for runtime quota detection.
def verify_host_login(host: str, timeout: int = 30) -> tuple[str, str]:
    """Local-only check: CLI in PATH + credentials file exists. Zero token.

    Returns (status, detail) where status is:
      'ok_locally'     — CLI installed AND local credentials present
      'cli_missing'    — host CLI not found in PATH
      'not_logged_in'  — CLI present but no local credential file
    Quota state is NOT predicted here — only knowable on real call failure.
    """
    if host not in CLI_MAP:
        return "cli_missing", f"未知 host: {host}"
    bin_name = CLI_MAP[host][0][0]
    if not shutil.which(bin_name):
        return "cli_missing", f"找不到 {bin_name} CLI"
    if not check_login_state(host):
        return "not_logged_in", f"找不到 {host} 本地憑證檔，可能尚未登入"
    return "ok_locally", "本地憑證已存在（未實際呼叫 AI，未消耗配額）"


# ─── Update check helpers ───────────────────────────────────────
def runtime_has_updates(genecr_dir: Path) -> bool:
    """Return True if runtime is behind origin (after `git fetch`)."""
    if not genecr_dir or not (genecr_dir / ".git").exists():
        return False
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0  # type: ignore[attr-defined]
        subprocess.run(["git", "-C", str(genecr_dir), "fetch", "--quiet"],
                       capture_output=True, timeout=15, creationflags=creationflags)
        r = subprocess.run(["git", "-C", str(genecr_dir), "rev-list", "HEAD..@{u}", "--count"],
                           capture_output=True, text=True, timeout=10, creationflags=creationflags)
        return int((r.stdout or "0").strip() or "0") > 0
    except Exception:
        return False


def upgrade_runtime(genecr_dir: Path, log) -> bool:
    """Run setup upgrade for the runtime; return True on success."""
    # Python-native upgrade: git pull + redeploy
    try:
        host = detect_host(genecr_dir) or "gemini"
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0  # type: ignore[attr-defined]
        subprocess.run(["git", "-C", str(genecr_dir), "pull", "--ff-only"],
                       capture_output=True, timeout=60, creationflags=creationflags)
        return deploy_genecr_python_native(host, log)
    except Exception as e:
        log(f"❌ {e}")
        return False
    # Legacy bash fallback (kept for non-Windows compatibility)
    cmd = ["bash", str(genecr_dir / "setup"), "upgrade"]
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0  # type: ignore[attr-defined]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace",
                                 creationflags=creationflags)
        for line in proc.stdout:
            log(line.rstrip())
        return proc.wait() == 0
    except Exception as e:
        log(f"❌ {e}")
        return False


def latest_gui_version() -> str | None:
    """Fetch latest release tag (e.g. 'v0.2.0' → '0.2.0') from GitHub API."""
    try:
        import urllib.request
        with urllib.request.urlopen(GENECR_RELEASES_API, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        return tag.lstrip("v") or None
    except Exception:
        return None


def _vtuple(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v))


class GenecrGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("780x980")
        self.minsize(680, 720)

        # Window icon — works for dev (.pyw) and PyInstaller bundle (sys._MEIPASS)
        try:
            base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
            ico = base / "icon.ico"
            if ico.exists() and sys.platform == "win32":
                self.iconbitmap(default=str(ico))
            png = base / "icon.png"
            if png.exists():
                self.iconphoto(True, tk.PhotoImage(file=str(png)))
        except Exception:
            pass

        self.genecr_dir = detect_genecr_dir()
        self.host = detect_host(self.genecr_dir) if self.genecr_dir else "unknown"
        self.python = find_python()
        self.proc = None
        self.run_dir: Path | None = None

        self._build_ui()

        if not self.genecr_dir:
            self.after(200, self._open_install_wizard)
        else:
            # Hide main window, show splash, check + apply updates, then re-show.
            self.withdraw()
            self.after(50, self._startup_update_check)

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
        self.host_combo = ttk.Combobox(top, textvariable=self.host_var, width=10,
                                        values=installed if installed else ["(未裝)"],
                                        state="readonly")
        self.host_combo.pack(side="left")
        self.host_combo.bind("<<ComboboxSelected>>", self._on_host_change)
        ttk.Button(top, text="➕ 新增 AI", width=11,
                   command=self._open_add_host_dialog).pack(side="left", padx=(6, 10))
        self.path_label = ttk.Label(top, text="", foreground="#666")
        self.path_label.pack(side="left")
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

        # Run / Cancel / Login area
        btn_row = ttk.Frame(self)
        btn_row.pack(pady=10)
        self.run_btn = ttk.Button(btn_row, text="🚀 開始生成", command=self._on_run)
        self.run_btn.pack(side="left", padx=4)
        self.cancel_btn = ttk.Button(btn_row, text="✋ 取消", command=self._on_cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=4)

        # Login slot — either a button (not logged in) or a label (logged in).
        # Conditional rendering driven by check_login_state() — zero token cost.
        self.login_slot = ttk.Frame(btn_row)
        self.login_slot.pack(side="left", padx=4)
        self.login_btn = None      # populated by _refresh_login_slot()
        self.login_label = None
        self._refresh_login_slot()

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

        # Spinner state for running step
        self._spin_step: str | None = None
        self._spin_idx: int = 0
        self._spin_frames = ["⏳", "⌛"]
        self.after(400, self._spin_tick)

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
        # Refresh combo values in case a new host was just installed
        self.host_combo.configure(values=list_installed_hosts() or ["(未裝)"])
        # Re-evaluate login state for the newly selected host (zero token)
        self._refresh_login_slot()

    def _refresh_login_slot(self):
        """Render either a status label (logged in) or an active button (not
        logged in) in the login slot. Driven by check_login_state — 0 token."""
        if not hasattr(self, "login_slot"):
            return
        # Clear current slot contents
        for w in self.login_slot.winfo_children():
            w.destroy()
        self.login_btn = None
        self.login_label = None
        if check_login_state(self.host):
            # Already logged in — show a non-clickable status label
            self.login_label = ttk.Label(
                self.login_slot,
                text=f"✅ 已登入 {self.host}（偵測到本地憑證）",
                foreground="#16a34a",
                font=("Microsoft JhengHei", 10),
            )
            self.login_label.pack(side="left")
        else:
            # Not logged in — show actionable button
            self.login_btn = ttk.Button(
                self.login_slot,
                text=f"🔑 登入 {self.host}",
                command=self._on_login_host,
            )
            self.login_btn.pack(side="left")

    def _open_add_host_dialog(self):
        """Show all 3 hosts with status; let user install + login any of them."""
        win = tk.Toplevel(self)
        win.title("新增 / 管理 AI host")
        win.geometry("560x460")
        win.transient(self)
        try: win.grab_set()
        except Exception: pass

        ttk.Label(win, text="選擇要新增的 AI", font=("Microsoft JhengHei", 13, "bold")
                   ).pack(pady=(20, 4))
        ttk.Label(win, text="同一台電腦可裝多個 AI；當一個配額用完時可切換到另一個。",
                   foreground="#555", wraplength=520).pack(pady=(0, 8))

        rows_frame = ttk.Frame(win)
        rows_frame.pack(fill="both", expand=True, padx=20, pady=8)

        # Order: Claude first (recommended fallback), then Gemini, then Codex
        host_order = ["claude", "gemini", "codex"]
        host_desc = {
            "claude": "Anthropic Claude — 推薦備用，品質最佳（需付費 API 或 Pro 訂閱）",
            "gemini": "Google Gemini — 有免費額度，配額用完每天會重置",
            "codex":  "OpenAI Codex — 需 ChatGPT Plus 訂閱",
        }
        rows = {}

        def render_rows():
            for w in rows_frame.winfo_children(): w.destroy()
            for h in host_order:
                cli_ok = host_cli_installed(h)
                gen_ok = host_genecr_installed(h)
                row = ttk.LabelFrame(rows_frame, text=f"  {h.upper()}  ")
                row.pack(fill="x", pady=4)
                top = ttk.Frame(row); top.pack(fill="x", padx=6, pady=4)
                cli_icon = "✅" if cli_ok else "❌"
                gen_icon = "✅" if gen_ok else "❌"
                status = f"{cli_icon} CLI    {gen_icon} genecr"
                ttk.Label(top, text=status, font=("Consolas", 10)).pack(side="left")
                ttk.Label(top, text=host_desc[h], foreground="#666",
                           wraplength=360, font=("Microsoft JhengHei", 9)).pack(side="left", padx=(12,0))
                btn_row = ttk.Frame(row); btn_row.pack(fill="x", padx=6, pady=(0,4))
                if not cli_ok:
                    ttk.Button(btn_row, text=f"安裝 {h.upper()} CLI",
                                command=lambda hh=h: install_cli(hh)).pack(side="left", padx=2)
                elif not gen_ok:
                    ttk.Button(btn_row, text="安裝 genecr 到此 host",
                                command=lambda hh=h: install_genecr(hh)).pack(side="left", padx=2)
                else:
                    ttk.Button(btn_row, text="🌐 登入 / 驗證",
                                command=lambda hh=h: do_login(hh)).pack(side="left", padx=2)
                    ttk.Button(btn_row, text="切換到此 host",
                                command=lambda hh=h: switch_to(hh)).pack(side="left", padx=2)
                rows[h] = row

        log_frame = ttk.LabelFrame(win, text="進度")
        log_frame.pack(fill="x", padx=20, pady=4)
        log_text = tk.Text(log_frame, height=4, font=("Consolas", 9),
                            background="#1e1e1e", foreground="#ddd", state="disabled")
        log_text.pack(fill="x", padx=4, pady=4)
        def log(m):
            log_text.configure(state="normal")
            log_text.insert("end", m + "\n"); log_text.see("end")
            log_text.configure(state="disabled")

        def install_cli(host):
            cmd = PREREQ_INSTALL.get(host)
            if not cmd:
                log(f"❌ 不知怎麼裝 {host}"); return
            log(f"\n=== 安裝 {host} CLI ===")
            def worker():
                ok = self._wizard_run_blocking(cmd, log)
                self.after(0, render_rows)
                if not ok: self.after(0, lambda: log(f"✗ {host} CLI 安裝失敗"))
            threading.Thread(target=worker, daemon=True).start()

        def install_genecr(host):
            target = Path.home() / HOST_DIRS[host] / "skills" / "genecr"
            target.parent.mkdir(parents=True, exist_ok=True)
            log(f"\n=== 安裝 genecr 到 {host} ===")
            def worker():
                if not target.exists():
                    if not self._wizard_run_blocking(["git", "clone", GENECR_REPO_URL, str(target)], log):
                        return
                # Python-native deploy
                deploy_genecr_python_native(host, log)
                self.after(0, render_rows)
            threading.Thread(target=worker, daemon=True).start()

        def do_login(host):
            prev = self.host; self.host = host
            try:
                self._open_status_dialog("not_logged_in", "")
            finally:
                self.host = prev

        def switch_to(host):
            self.host_var.set(host)
            self._on_host_change()
            log(f"✓ 已切換到 {host}")

        render_rows()
        ttk.Button(win, text="關閉", command=win.destroy).pack(pady=8)

    def _on_login_host(self):
        """Triggered by login button. Re-checks credentials (user may have
        completed login externally), then either:
          - found credentials → flip slot to status label, done
          - still missing → directly run auto-login flow (no extra prompts)
        Zero token cost — only checks local files."""
        if check_login_state(self.host):
            # User logged in (perhaps externally) — refresh UI and stop
            self._refresh_login_slot()
            return
        # Still not logged in — open status dialog which contains 一鍵登入 button
        self._open_status_dialog(
            "not_logged_in",
            f"找不到 {self.host} 本地憑證，將開始登入流程。"
        )

    def _start_auto_login(self, parent_dialog, status_var):
        """Drive login per host:
           - gemini: spawn interactive, pipe /auth
           - codex:  spawn `codex login` (subcommand, opens browser)
           - claude: spawn `claude auth login` (subcommand, opens browser)
           Then poll verify_host_login until success."""
        host = self.host
        bin_path = shutil.which(host)
        if not bin_path:
            status_var.set(f"❌ 找不到 {host} CLI")
            return None

        # Per-host login command + whether to pipe stdin
        login_cmd_map = {
            "gemini": ([bin_path], "/auth\n"),                 # interactive + stdin
            "codex":  ([bin_path, "login"], None),             # subcommand
            "claude": ([bin_path, "auth", "login"], None),     # subcommand
        }
        cmd, stdin_input = login_cmd_map.get(host, ([bin_path], None))

        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0  # type: ignore[attr-defined]
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if stdin_input else None,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                creationflags=creationflags,
            )
            if stdin_input:
                try:
                    proc.stdin.write(stdin_input)
                    proc.stdin.flush()
                except Exception:
                    pass
            status_var.set(f"🌐 已啟動 {host} 登入流程，瀏覽器應即將開啟，請點選你的帳號…")
        except Exception as e:
            status_var.set(f"❌ 啟動失敗：{e}")
            return None

        # Poll verification every 3 seconds, max 3 minutes
        attempts = {"n": 0}
        max_attempts = 60  # 60 × 3s = 180s

        def poll():
            attempts["n"] += 1
            # Zero-token check: just look at whether credential file appeared
            if check_login_state(host):
                try: proc.terminate()
                except Exception: pass
                status_var.set("✅ 登入成功！可以開始使用了。")
                self._refresh_login_slot()  # main UI button → status label
                self.after(1500, parent_dialog.destroy)
                return
            if attempts["n"] >= max_attempts:
                try: proc.terminate()
                except Exception: pass
                status_var.set("⏱ 等待超時（3 分鐘）。請重試或檢查瀏覽器是否完成。")
                return
            status_var.set(f"🌐 等待瀏覽器登入完成…（已等 {attempts['n']*3} 秒）")
            self.after(3000, lambda: threading.Thread(target=poll, daemon=True).start())

        # First poll after 5s (give browser time to open + user time to click)
        self.after(5000, lambda: threading.Thread(target=poll, daemon=True).start())
        return proc

    def _open_status_dialog(self, status: str, detail: str):
        """Pop a guided dialog tailored to the actual problem (login / quota / network)."""
        host = self.host
        win = tk.Toplevel(self)
        win.transient(self)
        try: win.grab_set()
        except Exception: pass

        # ── Per-status content ─────────────────────────
        if status == "not_logged_in":
            title  = f"需要登入 {host}"
            icon   = "🔑"
            header = f"偵測到 {host} 尚未登入"
            steps_text = (
                f"請按下方「🌐 一鍵登入」，會自動：\n\n"
                f"  • 開啟瀏覽器\n"
                f"  • 你只要點選你的 Google 帳號\n"
                f"  • 完成後此視窗會自動關閉\n\n"
                f"全程不用碰命令列。"
            )
            show_login_btn = True
        elif status == "quota":
            title  = f"{host} 配額已用完"
            icon   = "⏱"
            header = "今日免費配額已耗盡"
            other_installed = [h for h in list_installed_hosts() if h != host]
            switch_hint = (f"\n\n💡 偵測到你也裝了 {' / '.join(other_installed)}，"
                            f"可以從上方下拉切換。") if other_installed else (
                "\n\n💡 建議按主畫面的「➕ 新增 AI」裝 Claude 當備用。")
            steps_text = (
                f"{host} 免費版每日有額度上限，已用完。\n\n"
                f"選項：\n"
                f"  • 等隔天 0:00（太平洋時間）配額自動重置\n"
                f"  • 升級付費版"
                + switch_hint
            )
            show_login_btn = False
        elif status == "network":
            title  = f"{host} 網路連線異常"
            icon   = "🌐"
            header = "網路連不上"
            steps_text = (
                "可能原因：\n"
                "  • 沒網路 / Wi-Fi 斷線\n"
                "  • 公司防火牆擋住 Google API\n"
                "  • VPN 異常\n\n"
                "請檢查網路後按「重新驗證」。"
            )
            show_login_btn = False
        else:  # unknown
            title  = f"{host} 狀態異常"
            icon   = "⚠"
            header = "偵測到問題，但原因不明"
            steps_text = "請看下方詳細訊息，或截圖給工程師。"
            show_login_btn = True  # offer login anyway

        win.title(title)
        win.geometry("560x440")

        ttk.Label(win, text=f"{icon} {header}",
                   foreground="#c00", font=("Microsoft JhengHei", 14, "bold")).pack(pady=(20, 4))

        ttk.Label(win, text=steps_text, foreground="#222", justify="left",
                   font=("Microsoft JhengHei", 10), wraplength=520).pack(padx=20, pady=10, anchor="w")

        if detail:
            det = ttk.LabelFrame(win, text="詳細訊息（給工程師看）")
            det.pack(fill="x", padx=20, pady=4)
            t = tk.Text(det, height=3, font=("Consolas", 8), background="#f5f5f5")
            t.insert("1.0", detail)
            t.configure(state="disabled")
            t.pack(fill="x", padx=4, pady=4)

        status_var = tk.StringVar(value="")
        ttk.Label(win, textvariable=status_var, foreground="#1e3a8a",
                   font=("Microsoft JhengHei", 10)).pack(pady=4)

        bar = ttk.Frame(win)
        bar.pack(pady=12)

        def auto_login():
            login_btn.configure(state="disabled")
            verify_btn.configure(state="disabled")
            self._start_auto_login(win, status_var)

        def verify():
            status_var.set("驗證中（檢查本地憑證，不消耗配額）…")
            verify_btn.configure(state="disabled")
            if show_login_btn: login_btn.configure(state="disabled")
            def worker():
                st, msg = verify_host_login(host, timeout=30)
                def done():
                    if st == "ok_locally":
                        status_var.set("✅ 已偵測到本地憑證。")
                        self._refresh_login_slot()
                        for w in bar.winfo_children(): w.destroy()
                        ttk.Button(bar, text="完成", command=win.destroy).pack(side="left", padx=4)
                    else:
                        status_var.set(f"❌ 仍未通過（{st}）。重開此視窗會顯示新狀態。")
                        verify_btn.configure(state="normal")
                        if show_login_btn: login_btn.configure(state="normal")
                self.after(0, done)
            threading.Thread(target=worker, daemon=True).start()

        if show_login_btn:
            login_btn = ttk.Button(bar, text=f"🌐 一鍵登入 {host}", command=auto_login)
            login_btn.pack(side="left", padx=4)
        verify_btn = ttk.Button(bar, text="🔄 重新驗證", command=verify)
        verify_btn.pack(side="left", padx=4)
        ttk.Button(bar, text="稍後", command=win.destroy).pack(side="left", padx=4)

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
            # Classify cause from err's content (which includes CLI stderr).
            # Don't make any extra AI calls — those would burn user tokens.
            kind = classify_call_failure(err)
            if kind == "quota":
                self._open_status_dialog("quota", err)
            elif kind == "not_logged_in":
                self._open_status_dialog("not_logged_in", err)
            elif kind == "network":
                self._open_status_dialog("network", err)
            else:
                self._open_status_dialog("unknown", err)
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
        self._spin_step = None
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

        pipeline_json = self.genecr_dir / "pipeline.json"
        pipeline_py = self.genecr_dir / "tools" / "bin" / "pipeline.py"

        cmd = [
            self.python, "-u",  # unbuffered stdout for live progress
            str(pipeline_py), str(pipeline_json),
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
            env["PYTHONUNBUFFERED"] = "1"  # critical: push print() lines to pipe immediately
            env["GENECR_HOST"] = self.host  # pipeline.py uses this to pick ai.commands[host]
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
                        self.after(0, self._set_step_running, val)
                        self.after(0, self._bump_progress, 1)
                    elif kind == "render_done" and val in self.step_labels:
                        self.after(0, self._set_step_done, val)
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

    def _set_step_running(self, step: str):
        self._spin_step = step

    def _set_step_done(self, step: str):
        if self._spin_step == step:
            self._spin_step = None
        self.step_labels[step].configure(text=f"✅  {STEP_LABELS[step]}")

    def _spin_tick(self):
        if self._spin_step and self._spin_step in self.step_labels:
            self._spin_idx = (self._spin_idx + 1) % len(self._spin_frames)
            frame = self._spin_frames[self._spin_idx]
            self.step_labels[self._spin_step].configure(
                text=f"{frame}  {STEP_LABELS[self._spin_step]} 生成中…"
            )
        self.after(400, self._spin_tick)

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

        prereqs = ["python", "node", "git", "gemini", "genecr"]
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
            # genecr is special — git clone + Python deploy
            if name == "genecr":
                target = Path.home() / ".gemini" / "skills" / "genecr"
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    if not self._wizard_run_blocking(["git", "clone", GENECR_REPO_URL, str(target)], log):
                        return False
                return deploy_genecr_python_native("gemini", log)

            # Try each method in PREREQ_METHODS in order
            methods = PREREQ_METHODS.get(name, [])
            for i, method in enumerate(methods, 1):
                kind = method[0]
                log(f"\n--- 嘗試方法 {i}/{len(methods)}：{kind} ---")
                ok = False
                if kind == "winget":
                    cmd = method[1]
                    if not check_prereq("winget"):
                        log("✗ winget 不存在，跳過此方法")
                        continue
                    ok = self._wizard_run_blocking(cmd, log)
                elif kind == "download":
                    url = method[1]; args = method[2]
                    ok = self._wizard_download_install(url, args, log)
                elif kind == "npm":
                    cmd = method[1]
                    ok = self._wizard_run_blocking(cmd, log)

                if ok and check_prereq(name):
                    log(f"✓ 方法 {i}（{kind}）成功")
                    return True
                log(f"✗ 方法 {i}（{kind}）失敗，嘗試下一個方法…")

            log(f"❌ 所有方法都失敗")
            return False

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
        # Auto-start install if anything missing — user doesn't need to click.
        if not all(check_prereq(n) for n in prereqs):
            log("檢測到缺少套件，3 秒後自動開始安裝…（要中止可關閉視窗）")
            self.after(3000, lambda: threading.Thread(target=auto_install, daemon=True).start())

    def _wizard_download_install(self, url: str, install_args: list[str], log) -> bool:
        """Download installer (.msi/.exe) from URL and run silently. Avoids winget."""
        import urllib.request, tempfile
        try:
            fname = url.split("/")[-1]
            tmp = Path(tempfile.gettempdir()) / fname
            log(f"⬇ 下載 {fname} …")
            with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
                total = int(r.headers.get("Content-Length", 0))
                downloaded = 0; chunk = 65536
                while True:
                    buf = r.read(chunk)
                    if not buf: break
                    f.write(buf); downloaded += len(buf)
                    if total and downloaded % (chunk * 16) < chunk:
                        self.after(0, log, f"  … {downloaded // 1024 // 1024} MB / {total // 1024 // 1024} MB")
            log(f"✓ 下載完成（{tmp.stat().st_size // 1024 // 1024} MB），開始安裝…")

            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0  # type: ignore[attr-defined]
            if str(tmp).lower().endswith(".msi"):
                cmd = ["msiexec", "/i", str(tmp)] + install_args
            else:
                cmd = [str(tmp)] + install_args
            log(f"$ {' '.join(cmd[:3])} ...")
            r2 = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                                  encoding="utf-8", errors="replace",
                                  creationflags=creationflags)
            if r2.returncode != 0:
                log(f"❌ 安裝失敗 exit {r2.returncode}: {r2.stderr[:300]}")
                return False
            log("✓ 安裝程式跑完")
            return True
        except Exception as e:
            log(f"❌ {e}")
            return False

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
        """Auto-login from wizard — same flow as main status dialog (no console)."""
        win = tk.Toplevel(parent)
        win.title("Gemini 登入中")
        win.geometry("440x180")
        win.transient(parent)
        try: win.grab_set()
        except Exception: pass
        ttk.Label(win, text="🌐 一鍵登入 Gemini",
                   font=("Microsoft JhengHei", 12, "bold")).pack(pady=(20, 6))
        ttk.Label(win, text="瀏覽器將自動開啟，請點選你的 Google 帳號。",
                   foreground="#555").pack()
        status_var = tk.StringVar(value="準備中…")
        ttk.Label(win, textvariable=status_var,
                   foreground="#1e3a8a", wraplength=400).pack(pady=12, padx=20)
        ttk.Button(win, text="關閉", command=win.destroy).pack(pady=8)
        prev_host = self.host
        self.host = "gemini"
        try:
            self._start_auto_login(win, status_var)
        finally:
            self.host = prev_host

    def _restart(self):
        """Restart this app so the wizard's installs take effect."""
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            messagebox.showinfo("請手動重開", "安裝完成。請關閉並重新開啟視窗。", parent=self)
            self.destroy()

    # ─── Startup update check ──────────────────────────────────
    def _startup_update_check(self):
        splash = tk.Toplevel(self)
        splash.title("genecr")
        splash.geometry("420x180")
        splash.transient(self)
        splash.overrideredirect(True)
        # center
        splash.update_idletasks()
        x = (splash.winfo_screenwidth() - 420) // 2
        y = (splash.winfo_screenheight() - 180) // 2
        splash.geometry(f"+{x}+{y}")
        splash.configure(background="#1e293b")

        ttk.Label(splash, text="genecr", foreground="#fff", background="#1e293b",
                  font=("Microsoft JhengHei", 16, "bold")).pack(pady=(20, 4))
        status_var = tk.StringVar(value="檢查更新中…")
        ttk.Label(splash, textvariable=status_var, foreground="#cbd5e1", background="#1e293b",
                  font=("Microsoft JhengHei", 10)).pack(pady=4)
        bar = ttk.Progressbar(splash, mode="indeterminate", length=320)
        bar.pack(pady=10)
        bar.start(10)

        def set_status(s): self.after(0, status_var.set, s)

        def worker():
            new_gui_msg = None
            missing_prereqs: list[str] = []
            login_ok_status = "ok_locally"
            login_detail = ""

            # 1. Check runtime updates (existing)
            set_status("檢查 runtime 版本…")
            if runtime_has_updates(self.genecr_dir):
                set_status("正在更新 runtime（請稍候）…")
                ok = upgrade_runtime(self.genecr_dir, lambda l: None)
                if ok:
                    set_status("runtime 已更新 ✓")
                else:
                    set_status("runtime 更新失敗，仍可使用舊版")

            # 2. Component completeness check (every startup, not just first install)
            set_status("檢查必要元件是否完整…")
            for n in ["python", "node", "git", "gemini", "genecr"]:
                if not check_prereq(n):
                    missing_prereqs.append(n)

            # 3. Login state check (zero token — file existence only)
            #    Only meaningful if no components missing for the current host
            if not missing_prereqs:
                set_status(f"檢查 {self.host} 登入狀態（不消耗 AI 配額）…")
                login_ok_status, login_detail = verify_host_login(self.host)

            # 4. GUI version check (existing)
            set_status("檢查 GUI 版本…")
            latest = latest_gui_version()
            if latest and _vtuple(latest) > _vtuple(APP_VERSION):
                new_gui_msg = (latest, APP_VERSION)

            # Done — show main window, then handle issues in priority order
            def finish():
                bar.stop()
                splash.destroy()
                self.deiconify()
                # Priority 1: missing components — block work until fixed
                if missing_prereqs:
                    self._notify_missing_prereqs(missing_prereqs)
                # Priority 2: not logged in (only if components are fine)
                elif login_ok_status == "not_logged_in":
                    self._open_status_dialog("not_logged_in", login_detail)
                # Priority 3: GUI update available (non-blocking)
                if new_gui_msg:
                    self._notify_new_gui(*new_gui_msg)
            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def _notify_missing_prereqs(self, missing: list):
        """Pop a dialog when one or more required components are missing
        (detected at startup, after initial install)."""
        win = tk.Toplevel(self)
        win.title("元件缺失")
        win.geometry("480x320")
        win.transient(self)
        try: win.grab_set()
        except Exception: pass
        ttk.Label(win, text="⚠ 偵測到必要元件缺失",
                   foreground="#c00", font=("Microsoft JhengHei", 13, "bold")
                   ).pack(pady=(20, 6))
        names = "、".join(PREREQ_LABELS.get(n, n) for n in missing)
        ttk.Label(win, text=f"缺少：{names}", wraplength=440,
                   font=("Microsoft JhengHei", 11)).pack(padx=20, pady=8)
        ttk.Label(win, text="可能原因：被解除安裝、PATH 變動、或此機器從未裝過。\n"
                            "請按下方按鈕開啟安裝精靈，會自動補上。",
                   wraplength=440, foreground="#555").pack(padx=20, pady=4)
        bar = ttk.Frame(win)
        bar.pack(pady=14)
        def open_wizard():
            win.destroy()
            self._open_install_wizard()
        ttk.Button(bar, text="🔧 開啟安裝精靈", command=open_wizard).pack(side="left", padx=4)
        ttk.Button(bar, text="稍後再說", command=win.destroy).pack(side="left", padx=4)

    def _notify_new_gui(self, latest: str, current: str):
        win = tk.Toplevel(self)
        win.title("有新版 GUI 可用")
        win.geometry("440x200")
        ttk.Label(win, text=f"🎉 新版 v{latest} 已發布",
                   font=("Microsoft JhengHei", 12, "bold")).pack(pady=(20, 6))
        ttk.Label(win, text=f"目前安裝：v{current}", foreground="#666").pack()
        ttk.Label(win, text="請從下方按鈕下載最新 installer 並重新安裝（runtime 已自動更新）。",
                   wraplength=400, foreground="#555").pack(pady=8, padx=20)
        bar = ttk.Frame(win)
        bar.pack(pady=10)
        ttk.Button(bar, text="🌐 開啟下載頁",
                    command=lambda: webbrowser.open(GENECR_RELEASES_PAGE)).pack(side="left", padx=4)
        ttk.Button(bar, text="稍後再說", command=win.destroy).pack(side="left", padx=4)


if __name__ == "__main__":
    app = GenecrGUI()
    app.mainloop()
