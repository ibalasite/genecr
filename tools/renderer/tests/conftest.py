"""Shared pytest fixtures for renderer tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RENDERER_DIR = REPO_ROOT / "tools" / "renderer"
EXAMPLES_DIR = REPO_ROOT / "templates" / "examples"

if str(RENDERER_DIR) not in sys.path:
    sys.path.insert(0, str(RENDERER_DIR))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def examples_dir() -> Path:
    return EXAMPLES_DIR


@pytest.fixture(scope="session")
def render_module():
    import render
    return render


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / f"{name}.input.json").read_text(encoding="utf-8"))


@pytest.fixture
def spec_basic_example() -> dict:
    return _load_example("spec-basic")


@pytest.fixture
def spec_advanced_example() -> dict:
    return _load_example("spec-advanced")


@pytest.fixture
def assets_example() -> dict:
    return _load_example("assets")


@pytest.fixture
def bdd_example() -> dict:
    return _load_example("bdd")


@pytest.fixture
def scrum_example() -> dict:
    return _load_example("scrum")


@pytest.fixture
def prototype_example() -> dict:
    return _load_example("prototype")


@pytest.fixture
def docs_example() -> dict:
    return _load_example("docs")
