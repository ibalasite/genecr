"""Sandbox 入口：模擬 spec-basic step。

使用方式：
  python run_spec_basic.py <run_dir> [--ai-command "..."] [--max-rounds N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_orchestrated as po

DEFAULT_AI_COMMAND = "claude -p --output-format text < {prompt} > {output}"
ROLES = ["generator", "gen_fixer", "reviewer", "fixer", "tail_completer"]


def print_file_stats(run_dir: Path):
    rows = []
    for role in ROLES:
        prompt_f = run_dir / f"spec-basic.{role}.combined.prompt.md"
        output_f = run_dir / f"spec-basic.{role}.output.txt"
        if prompt_f.exists() and prompt_f.stat().st_size > 0:
            in_bytes = prompt_f.stat().st_size
            out_bytes = output_f.stat().st_size if output_f.exists() else 0
            rows.append((role, in_bytes, out_bytes))
    if rows:
        print(f"\n  prompt/output 大小:")
        for role, ib, ob in rows:
            print(f"    {role:<14} input {ib:>8,} bytes (~{ib//4:>5,} tok)"
                  f"  output {ob:>8,} bytes (~{ob//4:>5,} tok)")

        # 特別顯示 generator output 前 200 字，方便偵測「請授權寫入檔案」
        gen_out = run_dir / "spec-basic.generator.output.txt"
        if gen_out.exists():
            content = gen_out.read_text(encoding="utf-8", errors="replace")
            print(f"\n  generator output 前 200 字:")
            print(f"    {repr(content[:200])}")


def compare_with_gold(result: dict, gold: dict):
    print(f"\n比對黃金標準:")
    r_name = result.get("feature", {}).get("name", "")
    g_name = gold.get("feature", {}).get("name", "")
    r_slug = result.get("feature", {}).get("slug", "")
    g_slug = gold.get("feature", {}).get("slug", "")
    print(f"  feature.name : 黃金={g_name!r}  結果={r_name!r}  {'✅' if r_name else '❌ 空'}")
    print(f"  feature.slug : 黃金={g_slug!r}  結果={r_slug!r}  {'✅' if r_slug else '❌ 空'}")

    r_dryrun = result.get("dryrun")
    print(f"  dryrun       : {'✅ 有' if r_dryrun else '❌ null/缺'}")
    if r_dryrun:
        tc = r_dryrun.get("tech_counts", {})
        print(f"    api_endpoints={tc.get('api_endpoints')} db_tables={tc.get('db_tables')} redis_keys={tc.get('redis_keys')}")

    r_rc = result.get("resource_counts", {})
    g_rc = gold.get("resource_counts", {})
    print(f"  resource_counts.visual_total: 黃金={g_rc.get('visual_total')}  結果={r_rc.get('visual_total')}")
    print(f"  resource_counts.audio_total : 黃金={g_rc.get('audio_total')}  結果={r_rc.get('audio_total')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir")
    parser.add_argument("--ai-command", default=DEFAULT_AI_COMMAND)
    parser.add_argument("--max-rounds", type=int, default=None)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    brief_file = run_dir / "brief.txt"
    gold_path = run_dir / "spec-basic.input.json"

    if not brief_file.exists():
        print(f"❌ brief.txt 不存在: {brief_file}")
        sys.exit(1)

    label = Path(__file__).parent.name
    print(f"=== {label}/run_spec_basic.py ===")
    print(f"Run dir   : {run_dir}")
    print(f"AI command: {args.ai_command}")
    print()

    ai_cfg = {"command": args.ai_command}

    # 清除舊的 spec-basic sandbox 輸出，避免誤讀上次結果（鎖定時跳過）
    for role in ROLES:
        for suffix in (".combined.prompt.md", ".output.txt"):
            f = run_dir / f"spec-basic.{role}{suffix}"
            if f.exists():
                try:
                    f.unlink()
                except OSError:
                    pass

    t_start = time.time()
    result = po.orchestrated_call_ai_for_step(
        step_name="spec-basic",
        step_type="spec-basic",
        ai_cfg=ai_cfg,
        brief_file=brief_file,
        run_dir=run_dir,
        max_rounds=args.max_rounds,
        depends_on=[],
    )
    t_elapsed = time.time() - t_start

    print(f"\n{'='*50}")
    print(f"結果    : success={result.success}, rounds={result.attempts}")
    print(f"總耗時  : {t_elapsed:.1f}s ({t_elapsed/60:.1f} min)")
    print_file_stats(run_dir)

    if result.data:
        out_path = run_dir / f"spec-basic.{label}.sandbox.json"
        out_path.write_text(
            json.dumps(result.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n輸出儲存至: {out_path}")

        if gold_path.exists():
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
            compare_with_gold(result.data, gold)
    else:
        print("❌ 沒有產出 data")
        for issue in result.final_issues:
            print(f"  - {issue}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"\n❌ FATAL ERROR: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
