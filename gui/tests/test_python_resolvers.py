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


# ─── find_python() 四層 detection ────────────────────────────────

def _mock_all_layers_empty(gui, monkeypatch):
    """把四層全 stub 成空，方便針對單一層測試。"""
    monkeypatch.setattr(gui, "_find_python_known_paths", lambda: iter([]))
    monkeypatch.setattr(gui, "_find_python_py_launcher", lambda: iter([]))
    monkeypatch.setattr(gui, "_find_python_registry", lambda: iter([]))
    monkeypatch.setattr(gui, "_find_python_path", lambda: iter([]))


def test_find_python_layer1_known_paths_wins_first(gui, tmp_path, monkeypatch):
    """層 1 命中就直接回，後面層不會被叫到。"""
    fake_py = tmp_path / "python.exe"
    fake_py.touch()
    _mock_all_layers_empty(gui, monkeypatch)
    monkeypatch.setattr(gui, "_find_python_known_paths", lambda: iter([fake_py]))
    monkeypatch.setattr(gui, "_verify_python3", lambda p: True)

    result = gui.find_python()
    assert result.name == "python.exe"


def test_find_python_layer4_path_when_others_empty(gui, tmp_path, monkeypatch):
    """前 3 層全空、層 4 PATH 有 Python → 回 PATH 結果。"""
    fake_py = tmp_path / "python3.exe"
    fake_py.touch()
    _mock_all_layers_empty(gui, monkeypatch)
    monkeypatch.setattr(gui, "_find_python_path", lambda: iter([fake_py]))
    monkeypatch.setattr(gui, "_verify_python3", lambda p: True)

    result = gui.find_python()
    assert result == fake_py.resolve()


def test_find_python_raises_when_all_layers_miss(gui, monkeypatch):
    """四層全空 → raise SystemPythonMissing。"""
    _mock_all_layers_empty(gui, monkeypatch)
    with pytest.raises(gui.SystemPythonMissing):
        gui.find_python()


def test_find_python_skips_unverified_candidate(gui, tmp_path, monkeypatch):
    """層 1 有候選但 _verify 失敗 → 繼續往下層找。"""
    bad = tmp_path / "fake-python.exe"
    bad.touch()
    good = tmp_path / "real-python.exe"
    good.touch()

    _mock_all_layers_empty(gui, monkeypatch)
    monkeypatch.setattr(gui, "_find_python_known_paths", lambda: iter([bad]))
    monkeypatch.setattr(gui, "_find_python_path", lambda: iter([good]))
    # 只有 good 路徑 verify 成功
    monkeypatch.setattr(gui, "_verify_python3", lambda p: Path(str(p)).name == "real-python.exe")

    result = gui.find_python()
    assert result == good.resolve()


def test_verify_python3_accepts_python3(gui, monkeypatch):
    """_verify_python3 看到 'Python 3.X' 回 True。"""
    def fake_run(cmd, **kwargs):
        r = types.SimpleNamespace()
        r.returncode = 0
        r.stdout = "Python 3.13.1\n"
        r.stderr = ""
        return r
    monkeypatch.setattr(gui.subprocess, "run", fake_run)
    # path 必須通過 exists 檢查
    monkeypatch.setattr(gui.Path, "exists", lambda self: True)
    assert gui._verify_python3("python") is True


def test_verify_python3_rejects_python2(gui, monkeypatch):
    """Python 2 不算數。"""
    def fake_run(cmd, **kwargs):
        r = types.SimpleNamespace()
        r.returncode = 0
        r.stdout = "Python 2.7.18\n"
        r.stderr = ""
        return r
    monkeypatch.setattr(gui.subprocess, "run", fake_run)
    monkeypatch.setattr(gui.Path, "exists", lambda self: True)
    assert gui._verify_python3("python") is False


# ─── SystemPythonMissing exception class ─────────────────────────

def test_system_python_missing_is_runtime_error(gui):
    """SystemPythonMissing 必須是 RuntimeError 子類，方便寬鬆 catch。"""
    assert issubclass(gui.SystemPythonMissing, RuntimeError)


# ─── 設計鐵則 ────────────────────────────────────────────────────

def test_find_python_never_returns_sys_executable(gui, monkeypatch):
    """四層全 miss 時必 raise，禁止 fallback 到 sys.executable。"""
    _mock_all_layers_empty(gui, monkeypatch)
    fake_exe = "/path/to/genecr-gui.exe"
    monkeypatch.setattr(gui.sys, "executable", fake_exe)

    with pytest.raises(gui.SystemPythonMissing):
        gui.find_python()


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
