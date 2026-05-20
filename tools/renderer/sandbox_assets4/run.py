"""Sandbox 入口：模擬 assets step，完全獨立於正式 pipeline。

使用方式：
  python run.py <run_dir> [--ai-command "..."] [--max-rounds N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_orchestrated as po

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AI_COMMAND = "claude -p --output-format text < {prompt} > {output}"

ROLES = ["generator", "gen_fixer", "reviewer", "fixer", "tail_completer"]


def print_file_stats(run_dir: Path, label: str):
    """印出本輪產生的 prompt/output 檔案大小與 token 估算。"""
    rows = []
    for role in ROLES:
        prompt_f = run_dir / f"assets.{role}.combined.prompt.md"
        output_f = run_dir / f"assets.{role}.output.txt"
        if prompt_f.exists() and prompt_f.stat().st_size > 0:
            in_bytes = prompt_f.stat().st_size
            out_bytes = output_f.stat().st_size if output_f.exists() else 0
            rows.append((role, in_bytes, out_bytes))
    if rows:
        print(f"\n  [{label}] prompt/output 大小:")
        for role, ib, ob in rows:
            print(f"    {role:<14} input {ib:>8,} bytes (~{ib//4:>5,} tok)"
                  f"  output {ob:>8,} bytes (~{ob//4:>5,} tok)")


def compare_with_gold(result: dict, gold: dict):
    result_items = result.get("assets", [])
    gold_items = gold.get("assets", [])

    print(f"\n比對黃金標準:")
    print(f"  黃金: {len(gold_items)} items  結果: {len(result_items)} items")

    diff = abs(len(result_items) - len(gold_items))
    if diff == 0:
        print(f"  ✅ item 數量一致（{len(gold_items)}）")
    elif diff <= 3:
        print(f"  ⚠️  item 數量差 {diff}（小誤差）")
    else:
        print(f"  ❌ item 數量差距過大（{diff}）")

    gold_cats = set(i.get("category", "") for i in gold_items)
    result_cats = set(i.get("category", "") for i in result_items)
    missing = gold_cats - result_cats
    if missing:
        print(f"  ⚠️  缺少 category: {missing}")
    else:
        print(f"  ✅ 所有 category 都有（{len(result_cats)} 個）")

    required = ["id", "name", "type", "category", "owner_role",
                "output_format", "suggested_filename", "usage", "production_prompt"]
    empty_count = sum(
        1 for item in result_items for f in required if not item.get(f)
    )
    if empty_count:
        print(f"  ⚠️  {empty_count} 個必填欄位為空")
    else:
        print(f"  ✅ 所有必填欄位都有值")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir")
    parser.add_argument("--ai-command", default=DEFAULT_AI_COMMAND)
    parser.add_argument("--max-rounds", type=int, default=None)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    brief_file = run_dir / "brief.txt"
    gold_path = run_dir / "assets.input.json"

    if not brief_file.exists():
        brief_file = run_dir / "_sandbox_brief.txt"
        brief_file.write_text("", encoding="utf-8")

    print(f"=== sandbox_assets/run.py ===")
    print(f"Run dir   : {run_dir}")
    print(f"AI command: {args.ai_command}")
    print()

    pipeline_json = REPO_ROOT / "pipeline.json"
    pipeline_cfg = json.loads(pipeline_json.read_text(encoding="utf-8"))
    assets_step = next(s for s in pipeline_cfg["steps"] if s["name"] == "assets")

    ai_cfg = {"command": args.ai_command}

    t_start = time.time()
    result = po.orchestrated_call_ai_for_step(
        step_name="assets",
        step_type=assets_step["type"],
        ai_cfg=ai_cfg,
        brief_file=brief_file,
        run_dir=run_dir,
        max_rounds=args.max_rounds,
        depends_on=assets_step.get("depends_on", ["spec-basic"]),
    )
    t_elapsed = time.time() - t_start

    print(f"\n{'='*50}")
    print(f"結果    : success={result.success}, rounds={result.attempts}")
    print(f"總耗時  : {t_elapsed:.1f}s ({t_elapsed/60:.1f} min)")
    print_file_stats(run_dir, "最終")

    if result.data:
        out_path = run_dir / "assets.sandbox.json"
        out_path.write_text(
            json.dumps(result.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n輸出儲存至: {out_path}")

        if gold_path.exists():
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
            compare_with_gold(result.data, gold)
        else:
            print(f"（無黃金標準可比對）")
    else:
        print("❌ 沒有產出 data")
        for issue in result.final_issues:
            print(f"  - {issue}")


if __name__ == "__main__":
    main()
