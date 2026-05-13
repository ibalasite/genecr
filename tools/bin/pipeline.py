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
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import render as r

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO_ROOT / "output"


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


def load_pipeline(path: Path) -> tuple[dict, list[StepState]]:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    vars_ = {"slug": cfg["feature"]["slug"]}
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


def call_ai(step: StepState, ai_cfg: dict, brief_file: Path) -> bool:
    step.input_path.parent.mkdir(parents=True, exist_ok=True)
    if ai_cfg.get("stub_mode"):
        if not step.stub_fixture or not step.stub_fixture.exists():
            print(f"   [stub] no fixture for {step.name}")
            return False
        shutil.copy2(step.stub_fixture, step.input_path)
        print(f"   [stub] {step.stub_fixture.name} → {step.input_path}")
        return True

    # Substitute {brief_file} inside the prompt content itself, so the AI is
    # instructed to READ that file as its first step (not piped on stdin).
    # Match the env-var names exported by bin/genecr-env.sh — single source of
    # truth for runtime paths. Per-step dynamic paths (brief, output) use {…}.
    raw_prompt = step.prompt_path.read_text(encoding="utf-8")
    effective_prompt = (
        raw_prompt
        .replace("${GENECR_DIR}",       str(REPO_ROOT))
        .replace("${GENECR_TEMPLATES}", str(REPO_ROOT / "templates"))
        .replace("${GENECR_BIN}",       str(REPO_ROOT / "bin"))
        .replace("${GENECR_TOOLS}",     str(REPO_ROOT / "tools" / "bin"))
        .replace("${GENECR_ASSETS}",    str(REPO_ROOT / "assets"))
        .replace("${GENECR_REFERENCES}", str(REPO_ROOT / "references"))
        .replace("{brief_file}", str(brief_file))
        .replace("{output}",     str(step.input_path))
        .replace("{type}",       step.type)
    )
    combined_path = step.run_dir / f"{step.name}.combined.prompt.md"
    combined_path.write_text(effective_prompt, encoding="utf-8")

    cmd = ai_cfg["command"].format(
        prompt=str(combined_path),
        output=str(step.input_path),
        brief_file=str(brief_file),
    )
    print(f"   [ai ] {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True)
        return step.input_path.exists()
    except subprocess.CalledProcessError as e:
        print(f"   [ai ] FAILED: {e}")
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


def main(argv: list[str]) -> int:
    args = argv[1:]
    flags = {a for a in args if a.startswith("--")}
    positional = [a for a in args if not a.startswith("--")]

    # split: .json arg = pipeline file; rest joined = user brief
    pipeline_arg = next((p for p in positional if p.endswith(".json")), None)
    brief_arg = " ".join(p for p in positional if not p.endswith(".json")).strip()

    pipeline_path = Path(pipeline_arg or "pipeline.json").resolve()
    if not pipeline_path.exists():
        print(f"[error] pipeline file not found: {pipeline_path}")
        print(__doc__)
        return 1

    cfg, steps = load_pipeline(pipeline_path)
    ai_cfg = cfg.get("ai", {})
    slug = cfg["feature"]["slug"]
    run_dir = pick_run_dir(slug, force_new="--new" in flags)
    for s in steps:
        s.run_dir = run_dir

    # Persist / load brief.txt for this run.
    brief_file = run_dir / "brief.txt"
    if brief_arg:
        brief_file.write_text(brief_arg, encoding="utf-8")
        print(f"[brief] saved to {brief_file}")
    elif not brief_file.exists():
        # New run with no brief — write an empty file so AI commands don't break.
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

    run_once(steps, ai_cfg, brief_file)
    print_status(steps, run_dir)
    n_done = sum(1 for s in steps if s.output_exists and not s.output_stale)
    return 0 if n_done == len(steps) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
