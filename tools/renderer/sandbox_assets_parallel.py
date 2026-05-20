"""Sandbox：驗證 assets 總表 + 平行明細 新做法。

使用方式：
  python sandbox_assets_parallel.py <run_dir> [--dry] [--max-workers N]

  run_dir      : 有 spec-basic.input.json 的 pipeline run 目錄
  --dry        : 只做總表 + 分組，不呼叫明細 AI
  --max-workers: 平行 worker 數（預設 4）

流程：
  1. 讀 spec-basic.input.json 當 upstream
  2. AI 產總表（只有 5 欄：id/name/type/category/owner_role）
  3. 程式按 category 分組
  4. 平行呼叫 AI：各組補完整欄位
  5. 程式 merge → 完整 assets JSON
  6. 與黃金標準（assets.input.json）比對

目標：各明細組 output 小 → 不截斷；平行 → wall clock = 最慢那組。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"

CLAUDE_CANDIDATES = [
    "claude",
    r"C:\Users\ibala\AppData\Roaming\npm\claude.cmd",
]

# 總表只需這 5 欄
MASTER_FIELDS = ["id", "name", "type", "category", "owner_role"]

# 明細需要補的欄位
DETAIL_FIELDS = ["output_format", "suggested_filename", "usage", "spec", "production_prompt",
                 "negative_prompt"]


# ── AI 呼叫 ────────────────────────────────────────────────────────────────

def _call_ai(prompt: str, timeout: int = 300) -> str:
    for cli in CLAUDE_CANDIDATES:
        try:
            result = subprocess.run(
                [cli, "-p", "-"],
                input=prompt,
                capture_output=True, text=True, encoding="utf-8", timeout=timeout,
            )
            return result.stdout
        except FileNotFoundError:
            continue
    raise RuntimeError("找不到 claude CLI")


def _extract_json(raw: str) -> dict | list:
    """剝 prose 和 fenced block，parse JSON。"""
    s = raw.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        s = "\n".join(lines[1:]).strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    # 找第一個 { 或 [
    for ch, end in [('{', '}'), ('[', ']')]:
        idx = s.find(ch)
        if idx >= 0:
            try:
                return json.loads(s[idx:])
            except Exception:
                pass
    # json_repair fallback
    try:
        from json_repair import repair_json
        idx = min((s.find(c) for c in ['{', '['] if s.find(c) >= 0), default=0)
        return json.loads(repair_json(s[idx:]))
    except Exception:
        pass
    raise ValueError(f"無法 parse JSON，raw[:200]={repr(raw[:200])}")


# ── Step 1：產總表 ────────────────────────────────────────────────────────

MASTER_PROMPT = """你是資產清單規劃師。根據以下 spec-basic，列出這個 feature 需要的所有美術/音效/字型資產。

只輸出 JSON array，每個 item 只有這 5 個欄位：
- id: "ASSET-NNN"（三位數字，從 001 開始）
- name: 資產中文名稱
- type: image | animation | sound | font | video | particle 其中一種
- category: **必須完全對應 spec-basic.resource_counts 裡的子 key 名稱**（例如「氣球（5 階段大小）」「按鈕底圖」）
- owner_role: art | audio | engineer 其中一種

鐵律：
1. 只輸出 JSON array，不要任何 prose 或說明
2. 只輸出以上 5 欄，不要其他欄位
3. resource_counts 裡每個 type 下的每個 category key，都必須產生對應數量的 item
4. category 名稱必須與 resource_counts 的 key 完全一致（不可自行改名）
5. 每個 category 的 item 數量必須等於 resource_counts 裡的數值

spec-basic（重點看 resource_counts 欄位）:
```json
{spec_basic}
```
"""


def _extract_resource_counts(sb: dict) -> dict[str, dict[str, int]]:
    """從 SB 的 resource_counts 提取 type→{category→count} 的對應表。"""
    rc = sb.get("resource_counts", {})
    result = {}
    for type_key in ["image", "animation", "sound", "font", "particle", "video"]:
        if isinstance(rc.get(type_key), dict):
            result[type_key] = rc[type_key]
    return result


def _validate_master_vs_sb(master: list[dict], rc: dict[str, dict[str, int]]) -> list[str]:
    """程式驗：總表的 category/count 必須跟 SB resource_counts 一致。"""
    errors = []
    # 計算總表裡各 category 的數量
    actual: dict[str, int] = {}
    for item in master:
        cat = item.get("category", "")
        actual[cat] = actual.get(cat, 0) + 1

    # 對每個 SB 定義的 category 驗數量
    for type_key, cats in rc.items():
        for cat, expected_count in cats.items():
            got = actual.get(cat, 0)
            if got != expected_count:
                errors.append(f"{cat}: SB 要求 {expected_count} 個，總表有 {got} 個")

    # 反查：總表多出的 category（不在 SB resource_counts 裡）
    all_sb_cats = {cat for cats in rc.values() for cat in cats}
    for cat in actual:
        if cat and cat not in all_sb_cats:
            errors.append(f"總表多出不在 SB resource_counts 的 category: 「{cat}」")

    return errors


def gen_master(sb: dict, rc: dict[str, dict[str, int]]) -> list[dict]:
    prompt = MASTER_PROMPT.replace("{spec_basic}", json.dumps(sb, ensure_ascii=False, indent=2))
    print("① 呼叫 AI 產總表...")
    t0 = time.time()
    raw = _call_ai(prompt)
    elapsed = time.time() - t0
    result = _extract_json(raw)
    if not isinstance(result, list):
        raise ValueError(f"總表應為 list，得到 {type(result)}")
    # 驗 5 欄都在
    for item in result:
        for f in MASTER_FIELDS:
            if f not in item:
                item[f] = ""
    # 程式驗：必須與 SB resource_counts 一致
    errors = _validate_master_vs_sb(result, rc)
    status = "✅" if not errors else f"⚠️  {len(errors)} 個不一致"
    print(f"   總表完成：{len(result)} items，耗時 {elapsed:.1f}s  {status}")
    for e in errors:
        print(f"      - {e}")
    return result


# ── Step 2：按 category 分組 ──────────────────────────────────────────────

def group_by_category(master: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for item in master:
        cat = item.get("category", "其他")
        groups.setdefault(cat, []).append(item)
    return groups


# ── Step 3：各組補明細 ────────────────────────────────────────────────────

DETAIL_GEN_PROMPT = """你是資產規格撰寫師。以下是某個 feature 的一組美術資產清單（同一 category）。
請為每個 item 補齊以下欄位，輸出完整的 JSON array：

需要補的欄位：
- output_format: 檔案格式+解析度/位元率（例 "PNG 1080x1920 @2x"）
- suggested_filename: snake_case 含副檔名
- usage: 用在哪個畫面/觸發時機，至少 20 字
- spec: array of strings，每條一個規格
- production_prompt: 給 AI 或美術產出這資源的指引。視覺類寫英文 T2I prompt（subject+style+composition）；音效寫音色/長度/情境；字型寫字型風格/字重/字符集。≥ 15 字
- negative_prompt: （視覺類）英文，描述要避免的元素；非視覺類留空字串

規則：
1. 保留原有的 5 欄（id/name/type/category/owner_role），加上以上欄位
2. 只輸出 JSON array，不要任何 prose
3. production_prompt 只寫一次，不要重複寫 image_prompt

遊戲名稱：{feature_name}
Category：{category}

待補清單：
```json
{items}
```
"""

DETAIL_REVIEW_PROMPT = """你是獨立 reviewer。以下是資產明細組的 JSON array，請逐項檢查並回報問題。

檢查規則：
1. 每個 item 必須有這些非空欄位：output_format, suggested_filename, usage, spec, production_prompt
2. usage 至少 20 字
3. production_prompt 至少 15 字
4. 視覺類（type=image/animation/particle/video）的 production_prompt 必須含英文 T2I/T2V prompt
5. 音效類（type=sound）的 production_prompt 必須描述音色/長度/情境
6. spec 必須是非空 array

輸出格式：JSON object，格式如下：
{{"issues": [{{"id": "ASSET-xxx", "field": "欄位名", "detail": "問題描述"}}]}}
若無問題輸出：{{"issues": []}}

待審查的明細：
```json
{items}
```
"""

DETAIL_FIX_PROMPT = """你是獨立 fixer。根據以下 issues 列表，修正 JSON array 中對應的欄位。

規則：
1. 只修 issues 指到的欄位，其他欄位原封不動
2. 輸出完整的 JSON array（不是 patch，是完整輸出）
3. 不要任何 prose

Issues：
```json
{issues}
```

待修的明細：
```json
{items}
```
"""

DETAIL_REQUIRED = ["output_format", "suggested_filename", "usage", "spec", "production_prompt"]


def _check_detail_issues(items: list[dict]) -> list[dict]:
    """程式端快速驗：必填欄位不能空，usage/production_prompt 長度。"""
    issues = []
    for item in items:
        item_id = item.get("id", "?")
        for field in DETAIL_REQUIRED:
            val = item.get(field)
            if not val or (isinstance(val, list) and len(val) == 0):
                issues.append({"id": item_id, "field": field, "detail": f"{field} 為空"})
        usage = item.get("usage", "")
        if len(usage) < 20:
            issues.append({"id": item_id, "field": "usage", "detail": f"usage 只有 {len(usage)} 字，需 ≥ 20"})
        pp = item.get("production_prompt", "")
        if len(pp) < 15:
            issues.append({"id": item_id, "field": "production_prompt", "detail": f"production_prompt 只有 {len(pp)} 字，需 ≥ 15"})
    return issues


def run_detail_group_loop(
    category: str, items: list[dict], feature_name: str, max_rounds: int = 3
) -> tuple[str, list[dict], float, int]:
    """單組明細的 gen → review → fix 迴圈，finding=0 才結束。"""
    t0 = time.time()
    rounds = 0

    # gen
    gen_prompt = (DETAIL_GEN_PROMPT
                  .replace("{feature_name}", feature_name)
                  .replace("{category}", category)
                  .replace("{items}", json.dumps(items, ensure_ascii=False, indent=2)))
    raw = _call_ai(gen_prompt)
    current = _extract_json(raw)
    if not isinstance(current, list):
        raise ValueError(f"[{category}] generator 回傳非 list")

    while rounds < max_rounds:
        rounds += 1

        # tier 1: 程式驗
        prog_issues = _check_detail_issues(current)

        # tier 2: AI reviewer（獨立 subagent）
        review_prompt = (DETAIL_REVIEW_PROMPT
                         .replace("{items}", json.dumps(current, ensure_ascii=False, indent=2)))
        review_raw = _call_ai(review_prompt)
        try:
            review_obj = _extract_json(review_raw)
            ai_issues = review_obj.get("issues", []) if isinstance(review_obj, dict) else []
        except Exception:
            ai_issues = []

        all_issues = prog_issues + ai_issues

        # finding=0 gate（程式計數，不是 AI 自評）
        if len(all_issues) == 0:
            break

        # fixer（獨立 subagent）
        fix_prompt = (DETAIL_FIX_PROMPT
                      .replace("{issues}", json.dumps(all_issues, ensure_ascii=False, indent=2))
                      .replace("{items}", json.dumps(current, ensure_ascii=False, indent=2)))
        fix_raw = _call_ai(fix_prompt)
        try:
            fixed = _extract_json(fix_raw)
            if isinstance(fixed, list):
                current = fixed
        except Exception:
            pass  # fix 失敗就繼續用 current

    elapsed = time.time() - t0
    return category, current, elapsed, rounds


# ── Step 4：merge ──────────────────────────────────────────────────────────

def merge_groups(groups_results: dict[str, list[dict]]) -> list[dict]:
    """按原始 id 順序合併所有明細組。"""
    all_items = []
    for cat, items in groups_results.items():
        all_items.extend(items)
    # 按 id 排序
    def sort_key(item):
        try:
            return int(item.get("id", "ASSET-999").split("-")[1])
        except Exception:
            return 999
    all_items.sort(key=sort_key)
    return all_items


# ── 比對黃金標準 ─────────────────────────────────────────────────────────

def compare_with_gold(result: list[dict], gold: list[dict]):
    print(f"\n⑥ 與黃金標準比對:")
    print(f"   黃金: {len(gold)} items  結果: {len(result)} items")

    gold_ids = {i["id"] for i in gold}
    result_ids = {i["id"] for i in result}

    missing_ids = gold_ids - result_ids
    extra_ids = result_ids - gold_ids

    gold_cats = {}
    for i in gold:
        gold_cats.setdefault(i.get("category", "?"), 0)
        gold_cats[i.get("category", "?")] += 1

    result_cats = {}
    for i in result:
        result_cats.setdefault(i.get("category", "?"), 0)
        result_cats[i.get("category", "?")] += 1

    if missing_ids:
        print(f"   ⚠️  黃金有但結果缺少的 id: {sorted(missing_ids)}")
    if extra_ids:
        print(f"   ⚠️  結果多出的 id: {sorted(extra_ids)}")

    # 比對 category 覆蓋
    missing_cats = set(gold_cats) - set(result_cats)
    if missing_cats:
        print(f"   ⚠️  缺少的 category: {missing_cats}")
    else:
        print(f"   ✅ 所有 category 都有覆蓋（{len(result_cats)} 個）")

    # 比對必填欄位覆蓋率
    required_fields = ["id", "name", "type", "category", "owner_role",
                       "output_format", "suggested_filename", "usage", "production_prompt"]
    missing_fields_count = 0
    for item in result:
        for f in required_fields:
            if not item.get(f):
                missing_fields_count += 1
    if missing_fields_count:
        print(f"   ⚠️  {missing_fields_count} 個必填欄位為空")
    else:
        print(f"   ✅ 所有必填欄位都有值")

    # item 數量差異
    diff = abs(len(result) - len(gold))
    if diff == 0:
        print(f"   ✅ item 數量完全一致（{len(gold)}）")
    elif diff <= 3:
        print(f"   ⚠️  item 數量差 {diff}（可接受範圍）")
    else:
        print(f"   ❌ item 數量差距過大（{diff}）")


# ── 主流程 ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", help="pipeline run 目錄路徑")
    parser.add_argument("--dry", action="store_true", help="只做總表+分組，不呼叫明細 AI")
    parser.add_argument("--max-workers", type=int, default=4, help="平行 worker 數（預設 4）")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    sb_path = run_dir / "spec-basic.input.json"
    gold_path = run_dir / "assets.input.json"

    print(f"=== sandbox_assets_parallel.py ===")
    print(f"Run dir: {run_dir}")
    print()

    # 載入 spec-basic
    if not sb_path.exists():
        print(f"❌ 找不到 {sb_path}")
        return
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    feature_name = sb.get("feature", {}).get("name", "未知 feature")
    print(f"① Feature: {feature_name}")
    print(f"   SB size: {sb_path.stat().st_size:,} bytes")

    # 載入黃金標準
    gold_items = None
    if gold_path.exists():
        gold_data = json.loads(gold_path.read_text(encoding="utf-8"))
        gold_items = gold_data.get("assets", [])
        print(f"   黃金標準: {len(gold_items)} items")
    else:
        print(f"   黃金標準: 無（只看結構）")
    print()

    # Step 1: 總表
    t_total_start = time.time()
    master = gen_master(sb)

    # Step 2: 分組
    groups = group_by_category(master)
    print(f"\n② 分組結果（{len(groups)} 組）:")
    for cat, items in sorted(groups.items()):
        print(f"   [{len(items):2d}] {cat}")

    if args.dry:
        print("\n--dry 模式，不呼叫明細 AI，結束。")
        return

    # Step 3: 平行補明細
    print(f"\n③ 平行補明細（max-workers={args.max_workers}）...")
    detail_results: dict[str, list[dict]] = {}
    futures_map = {}

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        for cat, items in groups.items():
            future = executor.submit(run_detail_group_loop, cat, items, feature_name)
            futures_map[future] = cat

        for future in as_completed(futures_map):
            cat = futures_map[future]
            try:
                cat_result, items_result, elapsed, rounds = future.result()
                detail_results[cat] = items_result
                print(f"   ✅ [{cat}] {len(items_result)} items，{elapsed:.1f}s，{rounds} round(s)")
            except Exception as e:
                print(f"   ❌ [{cat}] 失敗: {e}")
                detail_results[cat] = groups[cat]  # fallback: 用總表的5欄

    # Step 4: merge
    print(f"\n④ 合併所有明細...")
    all_items = merge_groups(detail_results)
    result_data = {
        "feature": sb.get("feature", {}),
        "assets": all_items,
    }
    t_total = time.time() - t_total_start

    # 儲存
    out_path = run_dir / "assets.sandbox_parallel.json"
    out_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   合併完成：{len(all_items)} items")
    print(f"   結果儲存至: {out_path}")

    # Step 5: 比對
    if gold_items:
        compare_with_gold(all_items, gold_items)

    print(f"\n=== 總結 ===")
    print(f"總耗時     : {t_total:.1f}s（{t_total/60:.1f} min）")
    print(f"AI 呼叫次數: 1（總表）+ {len(groups)}（明細組，平行）= {1+len(groups)} 次")
    print(f"平行優勢   : {len(groups)} 組同時跑，wall clock << 串行總和")


if __name__ == "__main__":
    main()
