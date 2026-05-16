"""E2E one-step validator: run orchestrated_call_ai_for_step against a real
AI CLI. Default step = spec-basic. Limits token cost vs running full pipeline.

Usage:
    python scripts/e2e_single_step.py <run_dir> <brief.txt> [step_name]
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "renderer"))

from pipeline_orchestrated import orchestrated_call_ai_for_step


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    run_dir = Path(argv[1]).resolve()
    brief = Path(argv[2]).resolve()
    step = argv[3] if len(argv) > 3 else "spec-basic"

    run_dir.mkdir(parents=True, exist_ok=True)

    ai_cfg = {
        "command": "claude -p --output-format text < {prompt} > {output}",
    }

    print(f"=== E2E single-step: {step} ===")
    print(f"run_dir: {run_dir}")
    print(f"brief:   {brief}")
    print(f"AI cmd:  {ai_cfg['command']}\n")

    result = orchestrated_call_ai_for_step(
        step_name=step,
        step_type=step,
        ai_cfg=ai_cfg,
        brief_file=brief,
        run_dir=run_dir,
        # Use default max_rounds=20 (emergency cap, not convergence target).
        # Convergence rule is finding=0 enforced in review_loop.
    )
    print("\n=== RESULT ===")
    print(f"success: {result.success}")
    print(f"attempts: {result.attempts}")
    if result.final_issues:
        print(f"final issues ({len(result.final_issues)}):")
        for i in result.final_issues[:15]:
            print(f"  [{i.category}] {i.detail}")
    out_path = run_dir / f"{step}.input.json"
    if out_path.exists():
        size = out_path.stat().st_size
        print(f"output: {out_path} ({size:,} bytes)")
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
