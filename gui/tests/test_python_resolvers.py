"""TDD for genecr-gui Python resolvers.

兩個概念：
- embed_python(): 安裝工具包 Python，{安裝目錄}/python-embed/python.exe，檔不在就 raise
- find_python(): 主程式環境 Python（系統 PATH），找不到就 raise SystemPythonMissing

不准 fallback、不准回 sys.executable、不准回 None。
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

GUI_PYW = Path(__file__).resolve().parent.parent / "genecr-gui.pyw"


def _load_gui_module():
    """Load genecr-gui.pyw as a module (skipping tk init at import time)."""
    # tkinter import 在 module 頂層；test 環境多半沒 display 也沒問題（不 instantiate Tk）
    spec = importlib.util.spec_from_file_location("genecr_gui", GUI_PYW)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def gui():
    return _load_gui_module()


# ─── embed_python() ──────────────────────────────────────────────

def test_embed_python_returns_absolute_path_when_exists(gui, tmp_path, monkeypatch):
    """安裝工具包檔案存在 → 回絕對路徑。"""
    fake_app = tmp_path / "genecr-gui.exe"
    fake_app.touch()
    embed_dir = tmp_path / "python-embed"
    embed_dir.mkdir()
    embed_py = embed_dir / "python.exe"
    embed_py.touch()

    monkeypatch.setattr(gui.sys, "executable", str(fake_app))

    result = gui.embed_python()
    assert result == embed_py
    assert result.is_absolute()


def test_embed_python_raises_when_missing(gui, tmp_path, monkeypatch):
    """python-embed/python.exe 不存在 → raise RuntimeError（installer 不完整訊號）。"""
    fake_app = tmp_path / "genecr-gui.exe"
    fake_app.touch()
    # 故意不建 python-embed/
    monkeypatch.setattr(gui.sys, "executable", str(fake_app))

    with pytest.raises(RuntimeError, match="安裝工具包"):
        gui.embed_python()


# ─── find_python() ──────────────────────────────────────────────

def test_find_python_returns_path_when_python3_on_path(gui, monkeypatch):
    """PATH 上找到 python3 → 回絕對路徑。"""
    def fake_run(cmd, **kwargs):
        if cmd[0] == "python3":
            r = types.SimpleNamespace()
            r.returncode = 0
            r.stdout = "Python 3.13.1\n"
            return r
        raise FileNotFoundError
    monkeypatch.setattr(gui.subprocess, "run", fake_run)
    monkeypatch.setattr(gui.shutil, "which", lambda c: "/usr/bin/python3" if c == "python3" else None)

    result = gui.find_python()
    assert result == Path("/usr/bin/python3")


def test_find_python_falls_through_to_python_when_python3_missing(gui, monkeypatch):
    """python3 沒有但 python 有 → 回 python 路徑。"""
    def fake_run(cmd, **kwargs):
        if cmd[0] == "python3":
            raise FileNotFoundError
        if cmd[0] == "python":
            r = types.SimpleNamespace()
            r.returncode = 0
            r.stdout = "Python 3.13.1\n"
            return r
    monkeypatch.setattr(gui.subprocess, "run", fake_run)
    monkeypatch.setattr(gui.shutil, "which", lambda c: "C:/Python313/python.exe" if c == "python" else None)

    result = gui.find_python()
    assert result == Path("C:/Python313/python.exe")


def test_find_python_raises_when_no_python_on_path(gui, monkeypatch):
    """PATH 上完全沒 Python → raise SystemPythonMissing（caller 必須觸發 ensure_system_python）。"""
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError
    monkeypatch.setattr(gui.subprocess, "run", fake_run)
    monkeypatch.setattr(gui.shutil, "which", lambda c: None)

    with pytest.raises(gui.SystemPythonMissing):
        gui.find_python()


def test_find_python_raises_when_python2_only(gui, monkeypatch):
    """PATH 上只有 Python 2 → raise（不是 Python 3）。"""
    def fake_run(cmd, **kwargs):
        r = types.SimpleNamespace()
        r.returncode = 0
        r.stdout = "Python 2.7.18\n"
        return r
    monkeypatch.setattr(gui.subprocess, "run", fake_run)
    monkeypatch.setattr(gui.shutil, "which", lambda c: "/usr/bin/python")

    with pytest.raises(gui.SystemPythonMissing):
        gui.find_python()


# ─── SystemPythonMissing exception class ─────────────────────────

def test_system_python_missing_is_runtime_error(gui):
    """SystemPythonMissing 必須是 RuntimeError 子類，方便寬鬆 catch。"""
    assert issubclass(gui.SystemPythonMissing, RuntimeError)


# ─── 設計鐵則 ────────────────────────────────────────────────────

def test_find_python_never_returns_sys_executable(gui, monkeypatch):
    """禁止 fallback 回 sys.executable（這就是當初無限自我繁殖的元兇）。"""
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError
    monkeypatch.setattr(gui.subprocess, "run", fake_run)
    monkeypatch.setattr(gui.shutil, "which", lambda c: None)

    fake_exe = "/path/to/genecr-gui.exe"
    monkeypatch.setattr(gui.sys, "executable", fake_exe)

    try:
        result = gui.find_python()
    except gui.SystemPythonMissing:
        return  # 正確行為
    # 不該到這裡 — 如果走到，至少絕不能是 sys.executable
    pytest.fail(f"find_python 在找不到時應 raise，但回了 {result}（fallback 是禁止的）")


def test_embed_python_and_find_python_are_separate_concerns(gui):
    """兩支 helper 各司其職，路徑可以不同。"""
    # embed_python 看安裝目錄，find_python 看 PATH，回傳路徑邏輯完全獨立
    assert gui.embed_python.__name__ != gui.find_python.__name__
    # 兩支都該回 Path 物件（型別契約一致）
    import inspect
    sig_embed = inspect.signature(gui.embed_python)
    sig_find = inspect.signature(gui.find_python)
    assert sig_embed.return_annotation in (Path, "Path")
    assert sig_find.return_annotation in (Path, "Path")
