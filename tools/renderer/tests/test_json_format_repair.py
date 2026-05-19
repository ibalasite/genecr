"""Test _ensure_valid_json type-level loop（gen → check → program fix → check → AI fix → loop）

對應的 user 卡死案例：spec-basic generator 輸出 13332 字 JSON，line 1 col 13331 漏逗號。
要證明：
1. tier 1 程式 parse 對的就直接過
2. tier 2 json_repair 能修常見 AI 寫錯
3. tier 3 AI gen_fixer 在 program 修不了時介入
4. 無 iter cap，但 AI 兩次回同樣的東西會 break（避免無限）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from review_loop import _ensure_valid_json  # noqa: E402

import pytest


def _never_called(_raw, _err):
    raise AssertionError("gen_fixer should not have been called")


# ─── tier 1: 程式直接 parse ────────────────────────────────────

def test_valid_json_passes_tier1_no_ai():
    """合法 JSON 直接過、不呼 AI fixer。"""
    assert _ensure_valid_json('{"a": 1, "b": 2}', _never_called) == {"a": 1, "b": 2}


def test_fenced_json_passes_tier1():
    """markdown fence 包的 JSON 也直接過。"""
    raw = '```json\n{"a": 1}\n```'
    assert _ensure_valid_json(raw, _never_called) == {"a": 1}


# ─── tier 2: 程式 json_repair ───────────────────────────────────

def test_missing_comma_repaired_by_program_no_ai():
    """漏逗號 → json_repair 補 → 不呼 AI。"""
    raw = '{"a": 1 "b": 2}'  # 漏逗號（這次 user 卡的就是這種）
    result = _ensure_valid_json(raw, _never_called)
    assert result == {"a": 1, "b": 2}


def test_single_quotes_repaired_by_program():
    raw = "{'a': 'hello'}"
    assert _ensure_valid_json(raw, _never_called) == {"a": "hello"}


def test_trailing_comma_repaired_by_program():
    raw = '{"a": 1, "b": 2,}'
    assert _ensure_valid_json(raw, _never_called) == {"a": 1, "b": 2}


def test_truncated_object_repaired_by_program():
    """漏 closing }"""
    raw = '{"a": 1, "b": 2'
    result = _ensure_valid_json(raw, _never_called)
    assert result.get("a") == 1 and result.get("b") == 2


# ─── tier 3: AI gen_fixer ───────────────────────────────────────

def test_ai_fixer_kicks_in_when_program_fails():
    """造一個 json_repair 也救不了的 case → AI fixer 應被呼叫。"""
    # 用一個特殊的「不是 JSON-shaped」字串，讓 json_repair 也救不了
    bad_raw = "this is definitely not json at all just plain text"
    call_count = {"n": 0}
    def fake_fixer(raw, err):
        call_count["n"] += 1
        return '{"recovered": true}'  # AI 修好
    result = _ensure_valid_json(bad_raw, fake_fixer)
    assert result == {"recovered": True}
    assert call_count["n"] == 1


def test_loop_iterates_until_valid():
    """AI 第 1 次修不好、第 2 次修好 → 應 loop 兩次後成功。"""
    bad_raw = "garbage text not json"
    attempts = {"n": 0}
    def fake_fixer(raw, err):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return "still garbage maybe slightly different"
        return '{"finally": "ok"}'
    result = _ensure_valid_json(bad_raw, fake_fixer)
    assert result == {"finally": "ok"}
    assert attempts["n"] == 2


# ─── 剎車：AI 兩次回同樣的東西 ──────────────────────────────────

def test_breaks_when_ai_returns_same_output_3_times():
    """AI 連續 3 次回同樣的東西才 break（給 AI 兩次隨機性重試機會）。"""
    bad_raw = "garbage"
    call_count = {"n": 0}
    def stuck_fixer(raw, err):
        call_count["n"] += 1
        return "garbage"  # 永遠回同樣的
    with pytest.raises(ValueError, match="stalled.*3 times"):
        _ensure_valid_json(bad_raw, stuck_fixer)
    assert call_count["n"] == 3, f"應該被呼叫 3 次才放棄，實際 {call_count['n']}"


def test_breaks_when_ai_returns_empty_3_times():
    """AI 連續 3 次回空字串也視為卡住。"""
    bad_raw = "garbage"
    def empty_fixer(raw, err):
        return ""
    with pytest.raises(ValueError, match="stalled"):
        _ensure_valid_json(bad_raw, empty_fixer)


def test_does_not_break_if_ai_eventually_outputs_different():
    """AI 第 1、2 次出同樣的、第 3 次出不同 → 重置計數、繼續 loop。"""
    bad_raw = "garbage"
    sequence = ["garbage", "garbage", '{"finally": true}']  # 第 3 次給合法
    idx = {"n": 0}
    def variable_fixer(raw, err):
        out = sequence[idx["n"]]
        idx["n"] += 1
        return out
    result = _ensure_valid_json(bad_raw, variable_fixer)
    assert result == {"finally": True}
    assert idx["n"] == 3


# ─── User 真實案例 ──────────────────────────────────────────────

def test_user_real_case_missing_comma_at_position():
    """模擬 issue #11 spec-basic 的 13332 字 JSON 漏逗號（縮小版）。"""
    # 模擬一段「中間漏逗號」的 JSON
    raw = '{"feature": {"slug": "x", "name": "y"} "change_log": []}'
    result = _ensure_valid_json(raw, _never_called)
    assert result["feature"]["slug"] == "x"
    assert result["change_log"] == []
