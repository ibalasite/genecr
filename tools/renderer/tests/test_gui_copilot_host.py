from __future__ import annotations

import importlib.util
import json
import types
from pathlib import Path

import pytest


GUI_PYW = Path(__file__).resolve().parents[3] / "gui" / "genecr-gui.pyw"


def _load_gui_module():
    spec = importlib.util.spec_from_file_location("genecr_gui", GUI_PYW)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def gui():
    return _load_gui_module()


def test_gui_host_registry_includes_copilot(gui):
    assert gui.HOST_DIRS["copilot"] == ".copilot"
    assert gui.HOST_BIN["copilot"] == "copilot"
    assert gui.CLI_MAP["copilot"] == (["copilot"], ["-s"])


def test_detect_host_recognizes_copilot(gui, tmp_path: Path):
    runtime = tmp_path / ".copilot" / "skills" / "genecr"
    runtime.mkdir(parents=True)
    assert gui.detect_host(runtime) == "copilot"


def test_check_login_state_for_copilot_reads_logged_in_users(gui, tmp_path: Path, monkeypatch):
    config = tmp_path / ".copilot" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "lastLoggedInUser": {"host": "https://github.com", "login": "evans-bd"},
                "loggedInUsers": [{"host": "https://github.com", "login": "evans-bd"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(gui.Path, "home", lambda: tmp_path)
    assert gui.check_login_state("copilot") is True


def test_check_login_state_for_copilot_requires_logged_in_users(gui, tmp_path: Path, monkeypatch):
    config = tmp_path / ".copilot" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"firstLaunchAt": "2026-05-23T00:00:00Z"}), encoding="utf-8")
    monkeypatch.setattr(gui.Path, "home", lambda: tmp_path)
    assert gui.check_login_state("copilot") is False


def test_verify_host_login_for_copilot_uses_local_signal(gui, tmp_path: Path, monkeypatch):
    config = tmp_path / ".copilot" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps({"loggedInUsers": [{"host": "https://github.com", "login": "evans-bd"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(gui.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(gui.shutil, "which", lambda name: "C:/bin/copilot.exe" if name == "copilot" else None)
    status, detail = gui.verify_host_login("copilot")
    assert status == "ok_locally"
    assert "本地憑證已存在" in detail


def test_extract_slug_name_uses_copilot_stdin_mode(gui, monkeypatch):
    calls = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        calls["input"] = kwargs["input"]
        return types.SimpleNamespace(
            returncode=0,
            stdout='{"slug":"daily-checkin","name":"每日簽到"}',
            stderr="",
        )

    monkeypatch.setattr(gui.shutil, "which", lambda name: "C:/bin/copilot.exe" if name == "copilot" else None)
    monkeypatch.setattr(gui.subprocess, "run", fake_run)
    data, err = gui.extract_slug_name("每日簽到送獎勵", "copilot", timeout=60)
    assert err is None
    assert data == {"slug": "daily-checkin", "name": "每日簽到"}
    assert calls["cmd"] == ["C:/bin/copilot.exe", "-s"]
    assert "每日簽到送獎勵" in calls["input"]
