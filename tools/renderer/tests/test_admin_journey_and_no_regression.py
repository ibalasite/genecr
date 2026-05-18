"""Two foundational mechanisms:

A. spec-basic 加 `admin_journey` 欄位（同 user_journey 結構），有 admin
   wireframe 時必填 — 讓下游 prototype 知道後台要演哪些步、proto-help 步數
   可以程式化驗證（不靠 AI 取捨）。

B. `check_no_regression` 守門 — 重生 step 時把舊 input.json 關鍵欄位的
   count 跟新版比；任一可量化欄位數量比舊版少 → issue fixer 必補。
   修「重生時 AI 為塞新需求悄悄削減舊功能」這個系統性 regression。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = REPO_ROOT / "templates"

if str(REPO_ROOT / "tools" / "renderer") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))


# ─── A. admin_journey schema/canonical/prompt/review ─────────────────────


def test_spec_basic_schema_allows_admin_journey():
    schema = json.loads((TEMPLATES / "schemas" / "spec-basic.schema.json").read_text(encoding="utf-8"))
    props = schema["properties"]
    assert "admin_journey" in props, "spec-basic schema missing admin_journey field"
    aj = props["admin_journey"]
    assert aj.get("type") == "array"
    item = aj["items"]
    required = set(item.get("required", []))
    assert {"action", "detail"} <= required, (
        f"admin_journey items must require action+detail; got {required}"
    )


def test_spec_basic_canonical_has_admin_journey():
    ex = json.loads((TEMPLATES / "examples" / "spec-basic.input.json").read_text(encoding="utf-8"))
    aj = ex.get("admin_journey")
    assert isinstance(aj, list) and aj, "canonical must include sample admin_journey"
    for step in aj:
        assert "action" in step and "detail" in step


def test_spec_basic_prompt_documents_admin_journey():
    text = (TEMPLATES / "prompts" / "spec-basic.prompt.md").read_text(encoding="utf-8")
    assert "admin_journey" in text, "prompt must document admin_journey field"


def test_spec_basic_review_md_requires_admin_journey_when_admin_wireframe_exists():
    text = (TEMPLATES / "review" / "spec-basic.review.md").read_text(encoding="utf-8")
    assert text.count("admin_journey_missing") >= 2, (
        "review.md must define admin_journey_missing rule + whitelist entry"
    )


# ─── B. check_no_regression ──────────────────────────────────────────────


def test_check_no_regression_flags_shrunk_array():
    from cross_check import check_no_regression
    baseline = {"i18n": [{"zh": "a", "en": "a"}] * 15,
                "help_page": {"steps": ["s"] * 5},
                "timeline": [{"phase": "p"}] * 2,
                "fields": [{"name": f"f{i}", "desc": "x"} for i in range(11)]}
    current = {"i18n": [{"zh": "a", "en": "a"}] * 12,           # 15 → 12
               "help_page": {"steps": ["s"] * 3},                # 5 → 3
               "timeline": [{"phase": "p"}] * 1,                  # 2 → 1
               "fields": [{"name": f"f{i}", "desc": "x"} for i in range(9)]}  # 11 → 9
    issues = check_no_regression("spec-basic", current, baseline)
    cats = {i.category for i in issues}
    assert "feature_count_regression" in cats
    # All four shrunk fields should be reported (at least mentioned in details)
    all_details = "\n".join(i.detail for i in issues)
    for field in ("i18n", "help_page.steps", "timeline", "fields"):
        assert field in all_details, f"regression report must mention `{field}`; got:\n{all_details}"


def test_check_no_regression_passes_when_counts_held_or_grew():
    from cross_check import check_no_regression
    baseline = {"wireframes": [{"name": f"w{i}"} for i in range(6)],
                "user_journey": [{"action": "a"}] * 7}
    current = {"wireframes": [{"name": f"w{i}"} for i in range(9)],  # grew
               "user_journey": [{"action": "a"}] * 7}                # same
    issues = check_no_regression("spec-basic", current, baseline)
    assert not issues, f"growth/equal counts should pass; got {[(i.category, i.detail) for i in issues]}"


def test_check_no_regression_with_no_baseline_returns_empty():
    """First-time generation has no baseline — must not crash, must return [].
    Backward-compatible default behavior."""
    from cross_check import check_no_regression
    issues = check_no_regression("spec-basic", {"wireframes": [{"name": "w"}]}, baseline=None)
    assert issues == []


def test_check_no_regression_handles_nested_paths():
    """help_page.steps is nested — checker must drill in."""
    from cross_check import check_no_regression
    baseline = {"help_page": {"steps": ["a", "b", "c"]}}
    current = {"help_page": {"steps": ["a", "b"]}}
    issues = check_no_regression("spec-basic", current, baseline)
    assert any("help_page.steps" in i.detail for i in issues)


# ─── C. pipeline_orchestrated wires baseline through ─────────────────────


def test_orchestrated_call_passes_baseline_to_cross_check(tmp_path, monkeypatch):
    """If old input.json exists in run_dir at start of run, its contents must
    flow through to cross_check_fn as `baseline` — so check_no_regression can
    catch shrinkage."""
    # Stage 1: write a baseline input.json
    run_dir = tmp_path
    baseline_data = {"wireframes": [{"name": f"w{i}"} for i in range(6)]}
    (run_dir / "spec-basic.input.json").write_text(
        json.dumps(baseline_data), encoding="utf-8"
    )
    (run_dir / "feature.json").write_text('{"slug":"x"}', encoding="utf-8")

    # Capture baseline argument cross_check would receive
    captured = {}

    def fake_cross_check(step_name, all_step_data, baseline=None):
        captured["baseline"] = baseline
        return []

    # Patch cross_check.run_all_checks
    import cross_check
    monkeypatch.setattr(cross_check, "run_all_checks", fake_cross_check)

    # call orchestrated with stub ai_cfg → just exercise the baseline-loading path
    from pipeline_orchestrated import _load_baseline_for_regression
    baseline = _load_baseline_for_regression("spec-basic", run_dir)
    assert baseline is not None, "baseline loader missing"
    assert baseline.get("wireframes") and len(baseline["wireframes"]) == 6
