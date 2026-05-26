#!/usr/bin/env python3
"""
GeneCR pipeline driver — file-based, idempotent, datetime-stamped runs.

Output convention:
    <repo_root>/output/<feature.slug>/<YYYYMMDD-HHMMSS>/
        ├── *.input.json     (AI-produced)
        ├── *.md             (renderer output)
        └── *.html           (renderer output)

A "run" = one timestamped directory. Each invocation picks the latest run for
that slug; if it's incomplete it resumes; else it creates a new timestamp.

Usage:
    python run_pipeline.py <pipeline.json>            # run / resume latest
    python run_pipeline.py <pipeline.json> --new      # force new timestamp dir
    python run_pipeline.py <pipeline.json> --status   # show latest, no work
    python run_pipeline.py <pipeline.json> --watch    # poll every 2s

Status is determined ONLY by filesystem state, never by stdout messages.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout/stderr so unicode markers (▶ ✓ ✅) work on Windows cp950.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass  # Python < 3.7 or non-tty stream

import render as r
from ai_command import format_ai_command, resolve_ai_command, run_ai_command

REPO_ROOT = Path(__file__).resolve().parents[2]
# Outputs live in the USER'S cwd (where they invoked genecr), NOT in runtime.
# This keeps the runtime install dir read-only/stateless and matches the rule
# in bin/genecr-env.sh: "skills may only write output/ to the user's CWD".
OUTPUT_ROOT = Path.cwd() / "output"


@dataclass
class StepState:
    name: str
    type: str
    prompt_path: Path
    input_filename: str
    output_filename: str
    stub_fixture: Path | None
    depends_on: list[str] = field(default_factory=list)
    run_dir: Path = field(default_factory=lambda: Path("."))

    @property
    def input_path(self) -> Path:
        return self.run_dir / self.input_filename

    @property
    def output_path(self) -> Path:
        return self.run_dir / self.output_filename

    @property
    def input_exists(self) -> bool:
        return self.input_path.exists()

    @property
    def output_exists(self) -> bool:
        return self.output_path.exists()

    @property
    def output_stale(self) -> bool:
        if not (self.output_exists and self.input_exists):
            return False
        return self.output_path.stat().st_mtime < self.input_path.stat().st_mtime

    def status(self, done_set: set[str]) -> str:
        unmet = [d for d in self.depends_on if d not in done_set]
        if unmet:
            return f"⏸  blocked by: {', '.join(unmet)}"
        if not self.input_exists:
            return "⏳ waiting AI"
        if not self.output_exists:
            return "🔧 ready to render"
        if self.output_stale:
            return "♻  stale (input newer)"
        return "✅ done"


def expand(s: str, vars_: dict) -> str:
    out = s
    for k, v in vars_.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def load_pipeline(path: Path, slug: str) -> tuple[dict, list[StepState]]:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    vars_ = {"slug": slug}
    steps = []
    for s in cfg["steps"]:
        steps.append(StepState(
            name=s["name"],
            type=s["type"],
            prompt_path=(base / expand(s["prompt"], vars_)).resolve() if "prompt" in s else Path(),
            input_filename=expand(s["input"], vars_),
            output_filename=expand(s["output"], vars_),
            stub_fixture=(base / s["stub_fixture"]).resolve() if "stub_fixture" in s else None,
            depends_on=s.get("depends_on", []),
        ))
    return cfg, steps


def pick_run_dir(slug: str, force_new: bool) -> Path:
    feature_dir = OUTPUT_ROOT / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    if not force_new:
        existing = sorted([d for d in feature_dir.iterdir() if d.is_dir()])
        if existing:
            return existing[-1]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    new_dir = feature_dir / stamp
    new_dir.mkdir(parents=True, exist_ok=True)
    return new_dir


def print_status(steps: list[StepState], run_dir: Path) -> None:
    done = {s.name for s in steps if s.output_exists and not s.output_stale}
    rel = run_dir.relative_to(REPO_ROOT) if run_dir.is_relative_to(REPO_ROOT) else run_dir
    print(f"\nRun: {rel}")
    print(f"{'─' * 78}")
    print(f"{'STEP':<16} {'INPUT':<7} {'OUTPUT':<7} STATUS")
    print(f"{'─' * 78}")
    for s in steps:
        i = "✓" if s.input_exists else "·"
        o = "✓" if s.output_exists else "·"
        print(f"{s.name:<16} {i:<7} {o:<7} {s.status(done)}")
    n_done = sum(1 for s in steps if s.output_exists and not s.output_stale)
    print(f"{'─' * 78}")
    print(f"Progress: {n_done}/{len(steps)} done\n")


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""


def _substitute(raw: str, brief_file: Path, output_path: Path, type_: str, extra: dict[str, str] | None = None) -> str:
    """Inline file CONTENTS (not paths) so the AI doesn't need Read tool / outside-cwd permission."""
    schema_path  = REPO_ROOT / "templates" / "schemas"  / f"{type_}.schema.json"
    example_path = REPO_ROOT / "templates" / "examples" / f"{type_}.input.json"
    run_dir = output_path.parent
    out = (
        raw
        .replace("{type}",            type_)
        .replace("{brief_content}",   _read_file(brief_file))
        .replace("{schema_content}",  _read_file(schema_path)  or "(no schema for this type)")
        .replace("{example_content}", _read_file(example_path) or "(no example for this type)")
        .replace("{previous_json}",   _read_file(output_path))
        # Cross-step content: any prior step's input.json can be embedded by name
        .replace("{spec_basic_content}",    _read_file(run_dir / "spec-basic.input.json"))
        .replace("{spec_advanced_content}", _read_file(run_dir / "spec-advanced.input.json"))
        .replace("{assets_content}",        _read_file(run_dir / "assets.input.json"))
        .replace("{bdd_content}",           _read_file(run_dir / "bdd.input.json"))
        .replace("{scrum_content}",         _read_file(run_dir / "scrum.input.json"))
        .replace("{prototype_content}",     _read_file(run_dir / "prototype.input.json"))
        # Legacy path-style placeholders (still substituted for any prompt that uses them)
        .replace("${GENECR_DIR}",       str(REPO_ROOT))
        .replace("${GENECR_TEMPLATES}", str(REPO_ROOT / "templates"))
        .replace("${GENECR_BIN}",       str(REPO_ROOT / "bin"))
        .replace("${GENECR_TOOLS}",     str(REPO_ROOT / "tools" / "bin"))
        .replace("${GENECR_ASSETS}",    str(REPO_ROOT / "assets"))
        .replace("${GENECR_REFERENCES}", str(REPO_ROOT / "references"))
        .replace("{brief_file}", str(brief_file))
        .replace("{output}",     str(output_path))
    )
    if extra:
        for k, v in extra.items():
            # extra may be a path (errors_file) → also offer {errors_content} via reading
            out = out.replace("{" + k + "}", str(v))
            if k.endswith("_file"):
                content_key = k[:-5] + "_content"
                out = out.replace("{" + content_key + "}", _read_file(Path(v)))
    return out


def _resolve_command(ai_cfg: dict) -> str:
    """Backward-compatible wrapper around the shared host-aware resolver."""
    return resolve_ai_command(ai_cfg)


_QUOTA_KEYWORDS = (
    "limit reached", "quota", "exceeded", "exhaust", "rate limit",
    "resource exhausted", "restricting models", "too many requests",
    "ratelimit", "429",
)


def _run_ai(ai_cfg: dict, prompt_path: Path, output_path: Path, brief_file: Path,
            quota_retry_max: int = 2, quota_retry_wait: int = 60) -> bool:
    """Run host CLI. Prefer explicit output file, then stdout/stderr, with quota retry."""
    raw_cmd = _resolve_command(ai_cfg)
    try:
        preview_cmd = format_ai_command(
            raw_cmd,
            prompt_path=prompt_path,
            output_path=output_path,
            brief_file=brief_file,
            repo_root=REPO_ROOT,
        )
    except Exception as e:
        print(f"      ✗ command format error: {e}")
        return False
    print(f"      $ {preview_cmd}")
    for retry in range(quota_retry_max + 1):
        try:
            result = run_ai_command(
                raw_cmd,
                prompt_path=prompt_path,
                output_path=output_path,
                brief_file=brief_file,
                repo_root=REPO_ROOT,
            )
        except Exception as e:
            print(f"      ✗ subprocess exception: {e}")
            return False

        content = result.content
        if result.returncode == 0 and content.strip():
            return True

        # Failure — surface stderr so the user / GUI can classify
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        print(f"      ✗ subprocess failed (exit {result.returncode}); stderr/stdout below:")
        if stderr:
            for line in stderr.splitlines()[:20]:
                print(f"        [stderr] {line}")
        if stdout and stdout != stderr:
            for line in stdout.splitlines()[:5]:
                print(f"        [stdout] {line}")
        # Quota detection — wait and retry once
        combined_low = (stderr + " " + stdout).lower()
        if retry < quota_retry_max and any(k in combined_low for k in _QUOTA_KEYWORDS):
            wait = quota_retry_wait * (retry + 1)
            print(f"      ⏱ 偵測到配額/限速關鍵字，等 {wait}s 後重試 ({retry + 1}/{quota_retry_max})…")
            time.sleep(wait)
            continue
        return False
    return False


def _validate_format(step: StepState) -> tuple[bool, str]:
    """Pure schema-format check. Returns (ok, error_text)."""
    try:
        data = r.load_input(step.input_path)
    except Exception as e:
        return False, f"JSON parse error: {e}"
    schema_path = REPO_ROOT / "templates" / "schemas" / f"{step.type}.schema.json"
    if not schema_path.exists():
        return True, ""  # no schema → pass by default
    try:
        from jsonschema import validate, ValidationError
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validate(instance=data, schema=schema)
        return True, ""
    except ValidationError as e:
        path = ".".join(str(p) for p in e.absolute_path) or "(root)"
        return False, f"at {path}: {e.message}"
    except Exception as e:
        return False, f"validator error: {e}"


def call_ai(step: StepState, ai_cfg: dict, brief_file: Path, max_loops: int = 3) -> bool:
    """Generate → validate → fix loop. Program controls flow; AI generates/fixes."""
    step.input_path.parent.mkdir(parents=True, exist_ok=True)

    if ai_cfg.get("stub_mode"):
        if not step.stub_fixture or not step.stub_fixture.exists():
            print(f"   [stub] no fixture for {step.name}")
            return False
        shutil.copy2(step.stub_fixture, step.input_path)
        print(f"   [stub] {step.stub_fixture.name} → {step.input_path}")
        return True

    # ─── Attempt 1: generate ───
    print(f"   ▸ {step.name}: generating (attempt 1/{max_loops})")
    raw = step.prompt_path.read_text(encoding="utf-8")
    combined = _substitute(raw, brief_file, step.input_path, step.type)
    combined_path = step.run_dir / f"{step.name}.combined.prompt.md"
    combined_path.write_text(combined, encoding="utf-8")
    if not _run_ai(ai_cfg, combined_path, step.input_path, brief_file):
        print(f"   ✗ {step.name}: AI did not produce output")
        return False

    ok, err = _validate_format(step)
    if ok:
        print(f"   ✓ {step.name}: format OK on attempt 1")
        return True
    print(f"   ⚠ {step.name}: format FAIL: {err}")

    # ─── Attempts 2..N: fix ───
    fix_template_path = REPO_ROOT / "templates" / "prompts" / "_fix.prompt.md"
    if not fix_template_path.exists():
        print(f"   ✗ {step.name}: no fix prompt template")
        return False
    fix_raw = fix_template_path.read_text(encoding="utf-8")

    for attempt in range(2, max_loops + 1):
        errors_file = step.run_dir / f"{step.name}.errors.{attempt - 1}.txt"
        errors_file.write_text(err, encoding="utf-8")
        print(f"   ▸ {step.name}: fixing (attempt {attempt}/{max_loops})")
        fix_combined = _substitute(fix_raw, brief_file, step.input_path, step.type, {"errors_file": str(errors_file)})
        fix_combined_path = step.run_dir / f"{step.name}.fix.{attempt}.combined.prompt.md"
        fix_combined_path.write_text(fix_combined, encoding="utf-8")
        if not _run_ai(ai_cfg, fix_combined_path, step.input_path, brief_file):
            print(f"   ✗ {step.name}: fix AI did not produce output")
            return False
        ok, err = _validate_format(step)
        if ok:
            print(f"   ✓ {step.name}: format OK on attempt {attempt}")
            return True
        print(f"   ⚠ {step.name}: still failing: {err}")

    print(f"   ✗ {step.name}: gave up after {max_loops} attempts")
    return False


def call_render(step: StepState) -> bool:
    try:
        data = r.load_input(step.input_path)
        r.validate_input(step.type, data)
        data = r.preprocess(step.type, data, step.input_path.parent)
        content = r.render(step.type, data)
        step.output_path.parent.mkdir(parents=True, exist_ok=True)
        step.output_path.write_text(content, encoding="utf-8")
        print(f"   [render] {step.type} → {step.output_path.name}")
        return True
    except SystemExit as e:
        print(f"   [render] FAILED: {e}")
        return False
    except Exception as e:
        print(f"   [render] FAILED: {type(e).__name__}: {e}")
        return False


def execute_one(step: StepState, ai_cfg: dict, done: set[str], brief_file: Path) -> bool:
    unmet = [d for d in step.depends_on if d not in done]
    if unmet:
        return False
    changed = False
    if not step.input_exists:
        print(f"\n▶ {step.name}: AI step")
        # Orchestrated mode: program-controlled generate→review→fix with
        # independent subagents (set "orchestrated": false in ai_cfg to use
        # legacy same-AI fix loop).
        if ai_cfg.get("orchestrated", True) and not ai_cfg.get("stub_mode"):
            from pipeline_orchestrated import orchestrated_call_ai_for_step
            result = orchestrated_call_ai_for_step(
                step_name=step.name,
                step_type=step.type,
                ai_cfg=ai_cfg,
                brief_file=brief_file,
                run_dir=step.input_path.parent,
                depends_on=step.depends_on,
                max_rounds=ai_cfg.get("max_rounds"),
            )
            if result.success:
                changed = True
                print(f"   ✓ {step.name}: orchestrated success after {result.attempts} round(s)")
            else:
                print(f"   ✗ {step.name}: {len(result.final_issues)} issue(s) unresolved after {result.attempts} round(s)")
                for issue in result.final_issues[:8]:
                    print(f"     [{issue.category}] {issue.detail}")
                return False
        else:
            if call_ai(step, ai_cfg, brief_file):
                changed = True
            else:
                return False
    if not step.output_exists or step.output_stale:
        print(f"▶ {step.name}: render step")
        if call_render(step):
            changed = True
    return changed


def run_once(steps: list[StepState], ai_cfg: dict, brief_file: Path) -> bool:
    any_change = False
    for _ in range(len(steps) + 1):
        changed_this_sweep = False
        done = {s.name for s in steps if s.output_exists and not s.output_stale}
        for s in steps:
            if execute_one(s, ai_cfg, done, brief_file):
                changed_this_sweep = True
                any_change = True
                done.add(s.name)
        if not changed_this_sweep:
            break
    return any_change


def _arg_value(args: list[str], key: str) -> str | None:
    """Extract --key=value or --key value from argv."""
    for i, a in enumerate(args):
        if a == key and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(key + "="):
            return a[len(key) + 1:]
    return None


def _latest_run_across_features() -> Path | None:
    if not OUTPUT_ROOT.exists():
        return None
    candidates = []
    for feat_dir in OUTPUT_ROOT.iterdir():
        if not feat_dir.is_dir():
            continue
        for run in feat_dir.iterdir():
            if run.is_dir():
                candidates.append(run)
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def main(argv: list[str]) -> int:
    args = argv[1:]
    # Strip --key value pairs out of "flags" detection
    consumed = set()
    for i, a in enumerate(args):
        if a in ("--slug", "--name") and i + 1 < len(args):
            consumed.add(i); consumed.add(i + 1)
    flags = {a for i, a in enumerate(args) if a.startswith("--") and i not in consumed}
    positional = [a for i, a in enumerate(args) if not a.startswith("--") and i not in consumed]

    pipeline_arg = next((p for p in positional if p.endswith(".json")), None)
    non_json_positional = [p for p in positional if not p.endswith(".json")]
    slug_arg = _arg_value(args, "--slug")
    name_arg = _arg_value(args, "--name")

    pipeline_path = Path(os.environ["GENECR_DIR"]) / "pipeline.json"
    if not pipeline_path.exists():
        print(f"[error] pipeline file not found: {pipeline_path}")
        print(__doc__)
        return 1

    # Detect step-name as positional → revalidate mode.
    # Load pipeline cfg early to know the step name vocabulary.
    _cfg_for_names = json.loads(pipeline_path.read_text(encoding="utf-8"))
    _all_step_names = {s["name"] for s in _cfg_for_names.get("steps", [])}
    revalidate_step = next((p for p in non_json_positional if p in _all_step_names), None)
    brief_arg = " ".join(p for p in non_json_positional if p != revalidate_step).strip()

    # Resolve slug + run_dir.
    # New run (--new or first ever): --slug REQUIRED.
    # Resume: --slug optional; if missing, use latest run across all features.
    if "--new" in flags or slug_arg:
        if not slug_arg:
            print("[error] --new requires --slug <name>  (e.g. --slug bingo)")
            return 1
        slug = slug_arg
        run_dir = pick_run_dir(slug, force_new="--new" in flags)
    else:
        latest = _latest_run_across_features()
        if not latest:
            print("[error] no existing run; provide --slug to start a new one")
            return 1
        run_dir = latest
        slug = run_dir.parent.name

    feature_file = run_dir / "feature.json"
    feature = {"slug": slug, "name": name_arg or slug}
    if feature_file.exists() and not name_arg:
        # Reuse stored name on resume
        try:
            stored = json.loads(feature_file.read_text(encoding="utf-8"))
            feature["name"] = stored.get("name", slug)
        except Exception:
            pass
    feature_file.write_text(json.dumps(feature, ensure_ascii=False, indent=2), encoding="utf-8")

    cfg, steps = load_pipeline(pipeline_path, slug)
    ai_cfg = cfg.get("ai", {})
    for s in steps:
        s.run_dir = run_dir

    # Persist / load brief.txt for this run.
    brief_file = run_dir / "brief.txt"
    if brief_arg:
        brief_file.write_text(brief_arg, encoding="utf-8")
        print(f"[brief] saved to {brief_file}")
    elif not brief_file.exists():
        brief_file.write_text("", encoding="utf-8")
        if "--status" not in flags and not ai_cfg.get("stub_mode"):
            print(f"[warn] no brief provided and no brief.txt found; AI may have nothing to work on")

    if "--status" in flags:
        print_status(steps, run_dir)
        return 0

    if "--watch" in flags:
        try:
            while True:
                run_once(steps, ai_cfg, brief_file)
                print_status(steps, run_dir)
                if all(s.output_exists and not s.output_stale for s in steps):
                    print("All steps complete.")
                    return 0
                time.sleep(2)
        except KeyboardInterrupt:
            return 0

    if revalidate_step:
        return _revalidate_one_step(revalidate_step, steps, ai_cfg, brief_file, run_dir)

    run_once(steps, ai_cfg, brief_file)
    print_status(steps, run_dir)
    n_done = sum(1 for s in steps if s.output_exists and not s.output_stale)
    return 0 if n_done == len(steps) else 1


def _revalidate_one_step(step_name: str, steps: list[StepState], ai_cfg: dict,
                          brief_file: Path, run_dir: Path) -> int:
    """Revalidate one named step against current rules.

    - If <step>.input.json exists → load + pass as initial_data → skip
      generator → run review/fix loop until finding=0.
    - If missing → full flow (generator + review/fix).
    - Always re-render afterwards (template may have changed).
    """
    step = next((s for s in steps if s.name == step_name), None)
    if step is None:
        print(f"[error] step '{step_name}' not in pipeline.json")
        return 1

    initial_data = None
    if step.input_exists:
        try:
            initial_data = json.loads(step.input_path.read_text(encoding="utf-8"))
            print(f"\n▶ {step.name}: revalidate (existing input loaded, skipping generator)")
        except Exception as e:
            print(f"[warn] {step.name}: failed to load existing input.json ({e}); falling back to full generation")
    else:
        print(f"\n▶ {step.name}: input.json missing — full generator + review/fix")

    from pipeline_orchestrated import orchestrated_call_ai_for_step
    result = orchestrated_call_ai_for_step(
        step_name=step.name,
        step_type=step.type,
        ai_cfg=ai_cfg,
        brief_file=brief_file,
        run_dir=step.input_path.parent,
        initial_data=initial_data,
        depends_on=step.depends_on,
    )
    if not result.success:
        print(f"   ✗ {step.name}: {len(result.final_issues)} issue(s) unresolved after {result.attempts} round(s)")
        for issue in result.final_issues[:8]:
            print(f"     [{issue.category}] {issue.detail}")
        return 1
    print(f"   ✓ {step.name}: success after {result.attempts} round(s)")

    # Always re-render (template may have changed).
    if step.output_path.exists():
        step.output_path.unlink()
    print(f"▶ {step.name}: render step (forced)")
    if not call_render(step):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
