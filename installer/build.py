"""installer/build.py — genecr Windows installer 一鍵打包。

職責（唯一入口）：
  1. 下載 python.org 官方 embeddable zip → 解壓到 gui/dist/python-embed/
  2. Patch python313._pth 開 import site → 跑 get-pip.py 啟用 pip
  3. 在 host 系統 Python 跑 PyInstaller 把 gui/genecr-gui.pyw 打包成 gui/dist/genecr-gui.exe
  4. 呼 ISCC.exe 編 installer/genecr-installer.iss → installer/dist/genecr-installer-*.exe

用法：
    python installer/build.py            # 完整跑一次
    python installer/build.py --skip-embed   # 跳過 embed 下載（之前下載過了）

純 Python stdlib，無第三方依賴。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

# 路徑（相對於 repo root，本檔案在 installer/build.py）
REPO = Path(__file__).resolve().parent.parent
GUI_DIR = REPO / "gui"
GUI_PYW = GUI_DIR / "genecr-gui.pyw"
GUI_DIST = GUI_DIR / "dist"
GUI_BUILD = GUI_DIR / "build"
EMBED_DIR = GUI_DIST / "python-embed"
INSTALLER_DIR = REPO / "installer"
ISS_FILE = INSTALLER_DIR / "genecr-installer.iss"

# 對齊 wizard PREREQ_METHODS["python"] 的版本，user 機器跟工具包同版
PYTHON_VERSION = "3.13.1"
EMBED_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}/"
    f"python-{PYTHON_VERSION}-embed-amd64.zip"
)
GETPIP_URL = "https://bootstrap.pypa.io/get-pip.py"


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def download(url: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    log(f"下載 {url}")
    with urllib.request.urlopen(url, timeout=120) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)
    log(f"  → {dst} ({dst.stat().st_size // 1024} KB)")


def prepare_embed_python(skip_download: bool = False) -> None:
    """下載 + 解壓 embed zip → patch _pth → 啟 pip。"""
    if EMBED_DIR.exists() and skip_download:
        log(f"跳過 embed（已存在 {EMBED_DIR}）")
        return

    if EMBED_DIR.exists():
        log(f"清除舊 {EMBED_DIR}")
        shutil.rmtree(EMBED_DIR)

    zip_path = GUI_BUILD / f"python-{PYTHON_VERSION}-embed.zip"
    if not zip_path.exists():
        download(EMBED_URL, zip_path)
    else:
        log(f"用 cache：{zip_path}")

    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    log(f"解壓到 {EMBED_DIR}")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(EMBED_DIR)

    # Patch _pth — 取消 "#import site" 註解，讓 pip site-packages 被認得
    pth = next(EMBED_DIR.glob("python*._pth"), None)
    if pth is None:
        raise RuntimeError(f"找不到 _pth 檔在 {EMBED_DIR}")
    txt = pth.read_text(encoding="utf-8")
    if "#import site" in txt:
        txt = txt.replace("#import site", "import site")
        pth.write_text(txt, encoding="utf-8")
        log(f"  patched {pth.name}：import site 已啟用")

    # 跑 get-pip.py
    getpip = GUI_BUILD / "get-pip.py"
    if not getpip.exists():
        download(GETPIP_URL, getpip)
    embed_py = EMBED_DIR / "python.exe"
    log("跑 get-pip.py …")
    r = subprocess.run(
        [str(embed_py), str(getpip), "--no-warn-script-location"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"get-pip 失敗：\n{r.stdout}\n{r.stderr}")
    log("  pip 已裝進 embed Python")


def read_installer_version() -> str:
    """從 .iss 讀 AppVersion — single source of truth。"""
    import re
    txt = ISS_FILE.read_text(encoding="utf-8")
    m = re.search(r'#define\s+AppVersion\s+"([^"]+)"', txt)
    if not m:
        raise RuntimeError(f"找不到 AppVersion in {ISS_FILE}")
    return m.group(1)


def sync_gui_version(version: str) -> bool:
    """把 .pyw 裡的 APP_VERSION 同步到指定版號。回 True 代表有改動。"""
    import re
    txt = GUI_PYW.read_text(encoding="utf-8")
    new = re.sub(r'APP_VERSION\s*=\s*"[^"]+"', f'APP_VERSION = "{version}"', txt, count=1)
    if new == txt:
        return False
    GUI_PYW.write_text(new, encoding="utf-8")
    return True


def build_gui_exe() -> None:
    """用系統 Python 跑 PyInstaller 把 GUI 打成 .exe。"""
    # 同步版號 — .iss 是 single source of truth，APP_VERSION 跟它走
    v = read_installer_version()
    if sync_gui_version(v):
        log(f"同步 APP_VERSION → {v}（.pyw 已更新）")
    else:
        log(f"APP_VERSION 已是 {v}")

    log("確保 PyInstaller / pillow 在系統 Python")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "pyinstaller", "pillow"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"pip install pyinstaller 失敗：\n{r.stderr}")

    # 確保 icon 存在（沿用 gui/make-icon.py）
    ico = GUI_DIR / "icon.ico"
    if not ico.exists():
        log("生成 icon …")
        subprocess.run([sys.executable, str(GUI_DIR / "make-icon.py")], check=True)

    # 確保 splash.png 存在（PyInstaller --splash bootloader 用）
    splash = GUI_DIR / "splash.png"
    if not splash.exists():
        log("生成 splash.png …")
        subprocess.run([sys.executable, str(GUI_DIR / "make-splash.py")], check=True)

    log("PyInstaller 打包 GUI (--onedir + --splash：bootloader 30ms 內就秀 splash)")
    source = GUI_DIR / "genecr-gui.pyw"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",       # 1 process + 秒開（取代 --onefile 的 bootloader+解壓）
        "--windowed",
        "--splash", str(splash),   # bootloader 層 splash，Python 起來前就顯示
        "--name", "genecr-gui",
        "--icon", str(ico),
        "--add-data", f"{ico}{os.pathsep}.",
        "--add-data", f"{GUI_DIR / 'icon.png'}{os.pathsep}.",
        "--distpath", str(GUI_DIST),
        "--workpath", str(GUI_BUILD / "pyinstaller"),
        "--specpath", str(GUI_DIR),
        str(source),
    ]
    r = subprocess.run(cmd, text=True)
    if r.returncode != 0:
        raise RuntimeError("PyInstaller 失敗")
    # --onedir 產出 gui/dist/genecr-gui/genecr-gui.exe + 同目錄 _internal/
    onedir = GUI_DIST / "genecr-gui"
    exe = onedir / "genecr-gui.exe"
    if not exe.exists():
        raise RuntimeError(f"未產出 {exe}")
    size_mb = exe.stat().st_size / (1024 * 1024)
    log(f"  → {exe} ({size_mb:.1f} MB) + 整個 {onedir.name}/ 目錄")


def compile_installer() -> None:
    """呼 ISCC.exe 編 .iss → installer/dist/genecr-installer-*.exe"""
    iscc = shutil.which("ISCC.exe") or shutil.which("iscc")
    if iscc is None:
        # 試常見裝路徑（含 winget per-user 路徑）
        candidates = [
            Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
            Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
            Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe",
        ]
        for p in candidates:
            if p.exists():
                iscc = str(p)
                break
    if iscc is None:
        raise RuntimeError("找不到 Inno Setup（ISCC.exe）")
    log(f"ISCC.exe = {iscc}")
    r = subprocess.run([iscc, str(ISS_FILE)], text=True)
    if r.returncode != 0:
        raise RuntimeError("ISCC 失敗")
    out = list((INSTALLER_DIR / "dist").glob("genecr-installer-*.exe"))
    if out:
        for f in out:
            log(f"  → {f} ({f.stat().st_size // 1024} KB)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-embed", action="store_true",
                    help="跳過 embed 下載與解壓（若已存在）")
    ap.add_argument("--skip-gui", action="store_true",
                    help="跳過 PyInstaller GUI build")
    ap.add_argument("--skip-installer", action="store_true",
                    help="跳過 ISCC")
    args = ap.parse_args()

    try:
        prepare_embed_python(skip_download=args.skip_embed)
        if not args.skip_gui:
            build_gui_exe()
        if not args.skip_installer:
            compile_installer()
        log("✅ 完成")
        return 0
    except Exception as e:
        log(f"❌ 失敗：{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
