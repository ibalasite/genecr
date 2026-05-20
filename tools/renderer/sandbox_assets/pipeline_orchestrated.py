"""Adapter wiring the legacy pipeline.py call_ai signature to the new
review_loop orchestration.

NOT yet activated in execute_one — this module sits ready for opt-in. To
switch the live pipeline over, change pipeline.execute_one's
`call_ai(step, ai_cfg, brief_file)` to `orchestrated_call_ai(...)` and
provide the role prompt paths via ai_cfg.

This separation lets the user review the rewire as an isolated, reversible
commit (vs. burying it in a larger refactor).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cross_check import run_all_checks
from review_loop import RunStepResult, run_step

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = Path(__file__).resolve().parent / "templates"


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception:
        return ""


def _load_all_upstream(step_name: str, run_dir: Path, depends_on: list[str] | None = None) -> dict:
    """Load upstream *.input.json siblings for cross_check + reviewer.

    If `depends_on` is given, load ONLY those (declared dependency graph
    from pipeline.json). This keeps fixer prompts small — claude CLI
    silently fails (exit 0, empty stdout) on prompts > ~50KB, and
    indiscriminately loading every sibling balloons the prompt to 165KB+.

    If `depends_on` is None, falls back to legacy behavior (glob all
    siblings) for backward compatibility with callers that don't know
    the dependency graph.
    """
    out = {}
    if depends_on is not None:
        for name in depends_on:
            f = run_dir / f"{name}.input.json"
            if f.exists():
                try:
                    out[name] = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    pass
        return out
    for f in run_dir.glob("*.input.json"):
        try:
            key = f.stem.replace(".input", "")
            out[key] = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return out


def _build_schema_validator(step_type: str):
    """Return (validate_fn, required_keys) using the step's jsonschema."""
    schema_path = TEMPLATES / "schemas" / f"{step_type}.schema.json"
    if not schema_path.exists():
        return lambda _data: [], []

    from jsonschema import Draft7Validator
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    required_keys = schema.get("required", [])

    def validate(data: dict) -> list[str]:
        errs = []
        for e in sorted(validator.iter_errors(data), key=lambda e: e.path):
            path = ".".join(str(p) for p in e.absolute_path) or "(root)"
            errs.append(f"{path}: {e.message}")
        return errs
    return validate, required_keys


def _format_role_prompt(role: str, step_type: str, payload: dict, brief_file: Path) -> str:
    """Build the combined prompt text for a given role from the role's
    template + payload. Returns the prompt string to feed AI subprocess."""
    if role == "generator":
        # Reuse the existing step prompt (already wires upstream in step 6)
        template = _read(TEMPLATES / "prompts" / f"{step_type}.prompt.md")
        # The legacy _substitute fills brief / schema / upstream content; we
        # replicate the essential subset here.
        replacements = {
            "{type}": step_type,
            "{brief_content}": _read(brief_file),
            "{schema_content}": _read(TEMPLATES / "schemas" / f"{step_type}.schema.json"),
            "{example_content}": _read(TEMPLATES / "examples" / f"{step_type}.input.json"),
        }
        # Upstream JSON blobs (already in payload["upstream"])
        for up_name, up_data in payload.get("upstream", {}).items():
            replacements["{" + up_name.replace("-", "_") + "_content}"] = json.dumps(
                up_data, ensure_ascii=False, indent=2
            )
        for k, v in replacements.items():
            template = template.replace(k, v or "")
        return template

    if role == "reviewer":
        template = _read(TEMPLATES / "prompts" / "_review.prompt.md")
        step_rules = _read(TEMPLATES / "review" / f"{step_type}.review.md")
        return (template
                .replace("{step_type}", step_type)
                .replace("{step_review_rules}", step_rules)
                .replace("{input_data}", json.dumps(payload["input"], ensure_ascii=False, indent=2))
                .replace("{upstream_outputs}", json.dumps(payload["upstream"], ensure_ascii=False, indent=2)))

    if role == "fixer":
        template = _read(TEMPLATES / "prompts" / "_fixer.prompt.md")
        return (template
                .replace("{step_type}", step_type)
                .replace("{input_data}", json.dumps(payload["input"], ensure_ascii=False, indent=2))
                .replace("{issues}", json.dumps(payload["issues"], ensure_ascii=False, indent=2))
                .replace("{upstream_outputs}", json.dumps(payload["upstream"], ensure_ascii=False, indent=2)))

    if role == "gen_fixer":
        # Type-level fixer：窄 prompt 只修 JSON 格式錯，不動內容
        template = _read(TEMPLATES / "prompts" / "_gen_fixer.prompt.md")
        return (template
                .replace("{step_type}", step_type)
                .replace("{raw_text}", payload["raw"])
                .replace("{parse_error}", payload["parse_error"]))

    if role == "tail_completer":
        # 截斷補完：保留前段，只補缺失尾巴
        template = _read(TEMPLATES / "prompts" / "_tail_completer.prompt.md")
        return (template
                .replace("{step_type}", step_type)
                .replace("{truncated_raw}", payload["truncated_raw"][-3000:])
                .replace("{missing_keys}", json.dumps(payload["missing_keys"], ensure_ascii=False)))

    raise ValueError(f"unknown role: {role}")


def make_subprocess_invoker(
    ai_command: str,
    step_type: str,
    brief_file: Path,
    work_dir: Path,
):
    """Construct an AIInvoker that shells out via the ai_command template.

    ai_command uses {prompt} and {output} placeholders (same as legacy
    pipeline.json ai.command). For each invocation:
      1. Write the role's combined prompt to a tmp file
      2. Run subprocess capturing stdout to a tmp output file
      3. Read and return the output text
    """
    def invoke(role: str, payload: dict) -> str:
        prompt_text = _format_role_prompt(role, step_type, payload, brief_file)
        prompt_path = work_dir / f"{step_type}.{role}.combined.prompt.md"
        output_path = work_dir / f"{step_type}.{role}.output.txt"
        prompt_path.write_text(prompt_text, encoding="utf-8")

        cmd = ai_command.format(prompt=str(prompt_path), output=str(output_path))
        print(f"   ▸ {role}: $ {cmd}")
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
        except Exception as e:
            return json.dumps({"error": f"subprocess exception: {e}"})

        # Some AI CLIs write to {output}; others to stdout. Prefer the file.
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path.read_text(encoding="utf-8")
        return r.stdout or r.stderr or ""

    return invoke


def _load_baseline_for_regression(step_name: str, run_dir: Path) -> dict | None:
    """Read the previous {step}.input.json (if exists) and also fall back to
    the most recent {step}.input.json.bak* — used as `baseline` so
    check_no_regression can detect AI silently shrinking arrays during regen.
    Returns None if no baseline available (first-time generation)."""
    candidates = [run_dir / f"{step_name}.input.json"]
    # Also check .bak* files (when forced regen has moved current input aside)
    candidates.extend(sorted(run_dir.glob(f"{step_name}.input.json.bak*"), reverse=True))
    for p in candidates:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return None


def orchestrated_call_ai_for_step(
    step_name: str,
    step_type: str,
    ai_cfg: dict,
    brief_file: Path,
    run_dir: Path,
    max_rounds: int | None = None,
    initial_data: dict | None = None,
    depends_on: list[str] | None = None,
) -> RunStepResult:
    """Run the program-orchestrated generate→review→fix loop for one step.

    `depends_on`: declared upstream step names (from pipeline.json). Only
    those input.json files are loaded — prevents fixer prompt bloat past
    claude CLI's ~50KB silent-fail threshold. If None, legacy glob-all
    behavior is used.

    If `initial_data` is provided, generator is skipped — the loop starts
    by reviewing that data against current rules (revalidate mode).
    On success, writes the final accepted data to {step}.input.json.
    """
    upstream = _load_all_upstream(step_name, run_dir, depends_on=depends_on)
    ai_command = ai_cfg.get("command") or list(ai_cfg.get("commands", {}).values())[0]

    # Snapshot baseline BEFORE regen — used by check_no_regression to detect
    # AI silently shrinking arrays.
    baseline = _load_baseline_for_regression(step_name, run_dir)

    invoker = make_subprocess_invoker(ai_command, step_type, brief_file, run_dir)
    schema_validate, schema_required_keys = _build_schema_validator(step_type)

    # cross_check 嚴格用 depends_on 過濾後的 upstream — 禁止跨步驟偷下游 sibling.
    def cross_check_with_baseline(step_name_arg, all_step_data):
        return run_all_checks(step_name_arg, all_step_data, baseline=baseline)

    result = run_step(
        step_name=step_name,
        all_data=upstream,
        ai_invoker=invoker,
        schema_validate=schema_validate,
        cross_check_fn=cross_check_with_baseline,
        max_rounds=max_rounds,
        initial_data=initial_data,
        schema_required_keys=schema_required_keys,
    )

    if result.success and result.data is not None:
        out = run_dir / f"{step_name}.input.json"
        out.write_text(
            json.dumps(result.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return result
