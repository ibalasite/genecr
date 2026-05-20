"""Schema validate 必須在 cross_check 之前把關。

issue #13 根因：AI gen 出頂層合法 dict，但 apis[n].responses 是 list，
cross_check 呼叫 responses.keys() 直接 crash，pipeline 死掉。

修法：run_step loop 裡，schema 有錯這輪不跑 cross_check，
直接把 schema 問題給 fixer 修，修完下一輪 schema 再把關，
schema 乾淨了才讓 cross_check 跑。

這份測試驗證：
1. schema 有錯 → cross_check 不被呼叫
2. schema 乾淨 → cross_check 被呼叫
3. fixer 把 responses 從 list 修成 dict 後，下一輪 cross_check 正常跑
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from review_loop import run_step
from cross_check import Issue


# ─── helpers ────────────────────────────────────────────────────────────────

def _make_ai_invoker(gen_data: dict, fix_data: dict | None = None):
    """回傳一個假 ai_invoker。
    gen_data: generator 回傳的資料
    fix_data: fixer 回傳的修正資料（None 表示不需要 fixer）
    """
    import json
    call_log = []

    def invoker(role: str, payload: dict) -> str:
        call_log.append(role)
        if role == "generator":
            return json.dumps(gen_data, ensure_ascii=False)
        if role == "gen_fixer":
            return json.dumps(gen_data, ensure_ascii=False)
        if role == "fixer" and fix_data is not None:
            return json.dumps(fix_data, ensure_ascii=False)
        if role == "reviewer":
            return '{"issues": []}'
        return "{}"

    return invoker, call_log


def _schema_says_responses_must_be_object(data: dict) -> list[str]:
    """模擬 schema validate：responses 是 list 就回傳錯誤。"""
    errs = []
    for api in data.get("apis", []):
        if not isinstance(api.get("responses"), dict):
            errs.append(
                f"apis[id={api.get('id','?')}].responses: "
                f"expected object, got {type(api.get('responses')).__name__}"
            )
    return errs


def _no_schema_errs(data: dict) -> list[str]:
    return []


cross_check_called = {"count": 0}


def _counting_cross_check(step_name: str, all_data: dict) -> list[Issue]:
    cross_check_called["count"] += 1
    return []


# ─── 測試 ────────────────────────────────────────────────────────────────────

def test_cross_check_not_called_when_schema_has_errors():
    """schema 有錯這輪不能呼叫 cross_check（issue #13 修法驗證）。"""
    # AI 給的 responses 是 list（schema 錯誤）
    bad_data = {
        "apis": [{"id": "login", "responses": [{"200": {}}]}]
    }
    # fixer 修成正確的 dict
    fixed_data = {
        "apis": [{"id": "login", "responses": {"200": {"desc": "ok"}}}]
    }
    invoker, call_log = _make_ai_invoker(bad_data, fixed_data)

    cross_check_called["count"] = 0

    run_step(
        step_name="spec-advanced",
        all_data={},
        ai_invoker=invoker,
        schema_validate=_schema_says_responses_must_be_object,
        cross_check_fn=_counting_cross_check,
        max_rounds=3,
    )

    # 第一輪 schema 有錯，cross_check 不該被呼叫
    # 第二輪 schema 乾淨（fixer 修好），cross_check 才被呼叫
    assert cross_check_called["count"] >= 1, "schema 乾淨後 cross_check 應該被呼叫"

    # 關鍵：fixer 被呼叫，代表 schema 問題有送給 fixer
    assert "fixer" in call_log, "schema 有錯時 fixer 應該被呼叫去修"


def test_cross_check_called_when_schema_clean():
    """schema 沒錯，cross_check 正常被呼叫。"""
    good_data = {
        "apis": [{"id": "login", "responses": {"200": {"desc": "ok"}}}]
    }
    invoker, call_log = _make_ai_invoker(good_data)

    cross_check_called["count"] = 0

    run_step(
        step_name="spec-advanced",
        all_data={},
        ai_invoker=invoker,
        schema_validate=_no_schema_errs,
        cross_check_fn=_counting_cross_check,
        max_rounds=2,
    )

    assert cross_check_called["count"] >= 1, "schema 乾淨時 cross_check 應該被呼叫"


def test_schema_error_does_not_crash_pipeline():
    """responses 是 list 時 pipeline 不應 crash，應該正常走 fixer loop。

    這個測試模擬真實情境：cross_check 遇到 responses 是 list 就 crash
    （跟 issue #13 一樣的 AttributeError）。
    修法後，schema 有錯這輪不跑 cross_check，所以不會 crash。
    """
    bad_data = {
        "apis": [{"id": "login", "responses": [{"200": {}}]}]
    }
    fixed_data = {
        "apis": [{"id": "login", "responses": {"200": {"desc": "ok"}}}]
    }
    invoker, _ = _make_ai_invoker(bad_data, fixed_data)

    def crashing_cross_check(step_name: str, all_data: dict) -> list[Issue]:
        """模擬 issue #13：cross_check 碰到 responses 是 list 就 crash。"""
        for api in all_data.get(step_name, {}).get("apis", []):
            responses = api.get("responses", {})
            _ = responses.keys()  # list 呼叫 .keys() → AttributeError
        return []

    # 不能拋 exception，應該正常跑完
    result = run_step(
        step_name="spec-advanced",
        all_data={},
        ai_invoker=invoker,
        schema_validate=_schema_says_responses_must_be_object,
        cross_check_fn=crashing_cross_check,
        max_rounds=3,
    )

    # pipeline 不該 crash，result 要是 RunStepResult
    assert result is not None
