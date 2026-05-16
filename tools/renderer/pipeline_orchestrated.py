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

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "templates"


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception:
        return ""


def _load_all_upstream(step_name: str, run_dir: Path) -> dict:
    """Read every available *.input.json sibling so cross_check + reviewer
    can see the full graph."""
    out = {}
    for f in run_dir.glob("*.input.json"):
        try:
            key = f.stem.replace(".input", "")
            out[key] = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return out


def _build_schema_validator(step_type: str):
    """Return a callable(data) -> list[str] using the step's jsonschema."""
    schema_path = TEMPLATES / "schemas" / f"{step_type}.schema.json"
    if not schema_path.exists():
        return lambda _data: []

    from jsonschema import Draft7Validator
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    def validate(data: dict) -> list[str]:
        errs = []
        for e in sorted(validator.iter_errors(data), key=lambda e: e.path):
            path = ".".join(str(p) for p in e.absolute_path) or "(root)"
            errs.append(f"{path}: {e.message}")
        return errs
    return validate


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


def orchestrated_call_ai_for_step(
    step_name: str,
    step_type: str,
    ai_cfg: dict,
    brief_file: Path,
    run_dir: Path,
    max_rounds: int = 20,
) -> RunStepResult:
    """Run the program-orchestrated generate→review→fix loop for one step.

    Reads existing upstream *.input.json files from run_dir.
    On success, writes the final accepted data to {step}.input.json.
    """
    upstream = _load_all_upstream(step_name, run_dir)
    ai_command = ai_cfg.get("command") or list(ai_cfg.get("commands", {}).values())[0]

    invoker = make_subprocess_invoker(ai_command, step_type, brief_file, run_dir)
    schema_validate = _build_schema_validator(step_type)

    result = run_step(
        step_name=step_name,
        all_data=upstream,
        ai_invoker=invoker,
        schema_validate=schema_validate,
        cross_check_fn=run_all_checks,
        max_rounds=max_rounds,
    )

    if result.success and result.data is not None:
        out = run_dir / f"{step_name}.input.json"
        out.write_text(
            json.dumps(result.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return result
