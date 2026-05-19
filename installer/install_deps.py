"""install_deps.py — 給「安裝工具包 embed python」當入口跑的協調腳本。

任務：對指定的「系統 python」執行 pip install / playwright install，
讓套件落進系統 python 的 site-packages（pipeline 跑時看得到的地方）。

呼叫方式（從 GUI）：
    subprocess.run([embed_py, install_deps.py, sys_py, requirements.txt])

embed python 是「協調者」永遠在；system python 是「執行環境」收套件。
這份腳本本身用純 stdlib，可以在 embed python 上跑。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd, timeout=None):
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0  # type: ignore[attr-defined]
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        creationflags=creationflags, timeout=timeout,
    )


def pip_install(sys_py: str, req: Path) -> int:
    print(f"[install_deps] pip install -r {req}  (target = {sys_py})", flush=True)
    r = run([sys_py, "-m", "pip", "install", "-q", "-r", str(req)])
    if r.returncode != 0:
        print(f"[install_deps] pip 失敗：{r.stderr[:400]}", flush=True)
    return r.returncode


def playwright_install_chromium(sys_py: str) -> int:
    print(f"[install_deps] playwright install chromium  (target = {sys_py})", flush=True)
    r = run([sys_py, "-m", "playwright", "install", "chromium"], timeout=300)
    if r.returncode != 0:
        print(f"[install_deps] playwright 失敗：{r.stderr[:400]}", flush=True)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("system_python", help="系統 Python 的絕對路徑（套件裝這裡）")
    ap.add_argument("requirements", help="requirements.txt 路徑")
    ap.add_argument("--skip-playwright", action="store_true")
    args = ap.parse_args()

    sys_py = args.system_python
    req = Path(args.requirements)
    if not Path(sys_py).exists():
        print(f"[install_deps] 系統 Python 不存在：{sys_py}", flush=True)
        return 2
    if not req.exists():
        print(f"[install_deps] requirements 不存在：{req}", flush=True)
        return 2

    rc = pip_install(sys_py, req)
    if rc != 0:
        return rc
    if not args.skip_playwright:
        # playwright install 失敗不致命（prototype layout audit 才用得到），不擋 deploy
        playwright_install_chromium(sys_py)
    return 0


if __name__ == "__main__":
    sys.exit(main())
