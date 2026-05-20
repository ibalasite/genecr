"""Sandbox：用已知截斷案例實驗「補完尾巴」邏輯。

使用方式：
  python sandbox_truncation.py <run_dir> [--cut 0.9]

  run_dir  : 有 spec-advanced.fixer.output.txt 的 pipeline run 目錄
  --cut N  : 截斷點比例（預設 0.9 = 90%）

流程：
  1. 從 fixer.output.txt 取出完整 JSON（黃金標準）
  2. 人工截斷到 N%（模擬 generator 截斷）
  3. 偵測截斷 → 呼叫 AI 補完尾巴（新路徑）
  4. 拼接 → json_repair → parse → schema validate
  5. 比對結果與黃金標準，報告成功率 + 耗時

目標：不跑 generator（省 9 min），只跑一次補完 AI call（省 34 min fixer）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "templates" / "schemas" / "spec-advanced.schema.json"


# ── 工具函式 ────────────────────────────────────────────────────────────────

def extract_json_from_prose(raw: str) -> str:
    """剝掉 AI 在 JSON 前面加的 prose，找第一個 { 開始。"""
    idx = raw.find('{')
    if idx == -1:
        raise ValueError("找不到 { — 輸出不含 JSON")
    return raw[idx:]


def is_truncated(raw: str) -> bool:
    """判斷是否為截斷（開頭是 { 但 parse 失敗）。"""
    stripped = raw.strip()
    if not stripped.startswith('{'):
        return False
    try:
        json.loads(stripped)
        return False  # parse 成功，不是截斷
    except json.JSONDecodeError:
        return True


def missing_required_keys(partial: dict, schema: dict) -> list[str]:
    """找出 schema required 欄位中 partial dict 缺少的。"""
    required = schema.get("required", [])
    return [k for k in required if k not in partial]


def call_ai_completer(truncated_json: str, missing_keys: list[str]) -> str:
    """呼叫 claude CLI，請 AI 補完截斷 JSON 的尾巴。"""
    prompt = f"""你是一個 JSON 補完工具。以下 JSON 在生成時被截斷，前面的部分是完整且正確的。

請只輸出**從截斷點繼續補完的後段**，補到整個 JSON object 結束（最後一個 `}}`）。

規則：
1. 不要重複已有的內容，只補缺少的部分
2. 必須包含這些還沒出現的欄位：{missing_keys}
3. 輸出必須是合法的 JSON 片段，能和前段拼接後形成完整 JSON
4. 不要輸出任何 prose 或說明，只輸出 JSON 片段

截斷的 JSON（前段，從這裡接下去補）：
```
{truncated_json[-3000:]}
```
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False,
                                     encoding='utf-8') as f:
        f.write(prompt)
        prompt_file = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False,
                                     encoding='utf-8') as f:
        output_file = f.name

    # 嘗試多個可能的 claude CLI 路徑
    claude_candidates = [
        "claude",
        r"C:\Users\ibala\AppData\Roaming\npm\claude.cmd",
    ]
    try:
        for cli in claude_candidates:
            try:
                result = subprocess.run(
                    [cli, "-p", "-"],
                    input=prompt,
                    capture_output=True, text=True, encoding='utf-8', timeout=300
                )
                return result.stdout
            except FileNotFoundError:
                continue
        raise RuntimeError("找不到 claude CLI，請確認已安裝 Claude Code CLI")
    finally:
        Path(prompt_file).unlink(missing_ok=True)
        Path(output_file).unlink(missing_ok=True)


def stitch_and_parse(head: str, tail: str) -> dict:
    """拼接前後段，用 json_repair 修邊界，再 parse。"""
    # 找 head 的最後一個完整結構結尾
    # 嘗試直接拼接
    combined = head.rstrip() + "\n" + tail.lstrip()

    # 先試直接 parse
    try:
        return json.loads(combined)
    except json.JSONDecodeError:
        pass

    # 用 json_repair
    try:
        from json_repair import repair_json
        repaired = repair_json(combined)
        return json.loads(repaired)
    except Exception:
        pass

    raise ValueError("拼接後仍無法 parse，嘗試失敗")


def validate_schema(data: dict, schema: dict) -> list[str]:
    """用 jsonschema 驗證，回傳錯誤訊息列表。"""
    try:
        import jsonschema
        validator = jsonschema.Draft7Validator(schema)
        return [e.message for e in validator.iter_errors(data)]
    except ImportError:
        # fallback: 只驗 required keys
        missing = missing_required_keys(data, schema)
        return [f"missing required key: {k}" for k in missing]


def compare_keys(gold: dict, result: dict, prefix: str = "") -> list[str]:
    """粗略比對兩個 dict 的欄位結構差異。"""
    diffs = []
    for k in gold:
        full_k = f"{prefix}.{k}" if prefix else k
        if k not in result:
            diffs.append(f"缺少欄位: {full_k}")
        elif isinstance(gold[k], list) and isinstance(result.get(k), list):
            gold_len = len(gold[k])
            res_len = len(result[k])
            if abs(gold_len - res_len) > 1:
                diffs.append(f"{full_k}: 黃金={gold_len} items, 結果={res_len} items")
    for k in result:
        full_k = f"{prefix}.{k}" if prefix else k
        if k not in gold:
            diffs.append(f"多出欄位: {full_k}")
    return diffs


# ── 主流程 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", help="pipeline run 目錄路徑")
    parser.add_argument("--cut", type=float, default=0.9,
                        help="截斷點比例 0.0~1.0（預設 0.9）")
    parser.add_argument("--dry", action="store_true",
                        help="只做截斷偵測，不實際呼叫 AI")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    fixer_output = run_dir / "spec-advanced.fixer.output.txt"

    print(f"=== sandbox_truncation.py ===")
    print(f"Run dir : {run_dir}")
    print(f"Cut at  : {args.cut * 100:.0f}%")
    print()

    # 1. 載入黃金標準
    print("① 載入黃金標準（spec-advanced.fixer.output.txt）...")
    raw = fixer_output.read_text(encoding='utf-8')
    json_str = extract_json_from_prose(raw)
    gold = json.loads(json_str)
    print(f"   完整 JSON: {len(json_str):,} bytes, keys: {list(gold.keys())}")

    # 2. 人工截斷
    cut_byte = int(len(json_str) * args.cut)
    truncated = json_str[:cut_byte]
    print(f"\n② 人工截斷到 {args.cut*100:.0f}%（{cut_byte:,} bytes）")
    print(f"   截斷點附近: ...{repr(truncated[-60:])}...")
    print(f"   is_truncated() = {is_truncated(truncated)}")

    if not is_truncated(truncated):
        print("   截斷點剛好在 JSON 邊界，請調整 --cut 值")
        return

    # 3. 找缺少的 required keys（用 partial parse 估計）
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8')) if SCHEMA_PATH.exists() else {}
    # sandbox 有 gold，用 gold.keys() 當 authoritative；schema.required 可能不完整
    required = list(gold.keys())

    # 找到截斷前已出現哪些 top-level key
    appeared = []
    for k in required:
        if f'"{k}"' in truncated:
            appeared.append(k)

    missing = [k for k in required if k not in appeared]
    print(f"\n   已出現的 keys: {appeared}")
    print(f"   缺少的 keys  : {missing}")

    if args.dry:
        print("\n--dry 模式，不呼叫 AI，結束。")
        return

    # 4. 呼叫 AI 補完
    print(f"\n③ 呼叫 AI 補完尾巴（只補缺少的部分）...")
    t0 = time.time()
    try:
        tail_raw = call_ai_completer(truncated, missing)
    except RuntimeError as e:
        print(f"   ERROR: {e}")
        return
    elapsed = time.time() - t0
    print(f"   AI 耗時: {elapsed:.1f}s")
    print(f"   補完輸出大小: {len(tail_raw):,} bytes")
    print(f"   補完開頭: {repr(tail_raw[:100])}")

    # 5. 拼接 + parse
    print(f"\n④ 拼接 + json_repair + parse...")
    try:
        result = stitch_and_parse(truncated, tail_raw)
        print(f"   ✅ Parse 成功！keys: {list(result.keys())}")
    except ValueError as e:
        print(f"   ❌ Parse 失敗: {e}")
        return

    # 6. Schema validate
    if schema:
        errors = validate_schema(result, schema)
        if errors:
            print(f"\n⑤ Schema validate: ❌ {len(errors)} 個錯誤")
            for e in errors[:5]:
                print(f"   - {e}")
        else:
            print(f"\n⑤ Schema validate: ✅ 全通過")
    else:
        print(f"\n⑤ Schema validate: 跳過（找不到 schema 檔）")

    # 7. 與黃金標準比對
    diffs = compare_keys(gold, result)
    print(f"\n⑥ 與黃金標準比對:")
    if not diffs:
        print("   ✅ 結構完全一致")
    else:
        print(f"   ⚠️  {len(diffs)} 個差異:")
        for d in diffs:
            print(f"   - {d}")

    # 8. 儲存結果
    out_path = run_dir / "spec-advanced.sandbox_result.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n結果已儲存至: {out_path}")

    print(f"\n=== 總結 ===")
    print(f"AI 呼叫次數: 1（只補尾巴）vs 原本 2（fixer 重生 + 第二輪）")
    print(f"AI 耗時    : {elapsed:.1f}s vs 原本 ~2040s（34 min）")


if __name__ == "__main__":
    main()
