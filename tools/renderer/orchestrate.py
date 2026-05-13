#!/usr/bin/env python3
"""
GeneCR orchestrator — run all 7 renderers in order from a manifest.

Usage:
    python orchestrate.py <manifest.json>

Manifest schema:
{
  "feature": {"name": "...", "slug": "..."},
  "output_dir": "./output/<slug>",
  "inputs": {
    "spec-basic":    "path/to/spec-basic.input.json",
    "spec-advanced": "...",
    "assets":        "...",
    "bdd":           "...",
    "scrum":         "...",
    "prototype":     "...",
    "docs":          "..."
  }
}

Order of execution:
  1. spec-basic, spec-advanced, assets, bdd, scrum   (5 .md, can be parallel)
  2. prototype.html
  3. docs.html  (depends on the 5 .md outputs)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import render as r

ORDER = [
    ("spec-basic",    "{slug}-spec-basic.md"),
    ("spec-advanced", "{slug}-spec-advanced.md"),
    ("assets",        "{slug}-assets.md"),
    ("bdd",           "{slug}-bdd.md"),
    ("scrum",         "{slug}-scrum.md"),
    ("prototype",     "{slug}-prototype.html"),
    ("docs",          "{slug}-docs.html"),
]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1

    manifest_path = Path(argv[1]).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    slug = manifest["feature"]["slug"]
    out_dir = (manifest_path.parent / manifest["output_dir"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = manifest["inputs"]

    results = []
    for type_, name_pat in ORDER:
        if type_ not in inputs:
            print(f"[skip] {type_} (no input in manifest)")
            continue
        in_path = (manifest_path.parent / inputs[type_]).resolve()
        out_path = out_dir / name_pat.format(slug=slug)
        try:
            data = r.load_input(in_path)
            r.validate_input(type_, data)
            data = r.preprocess(type_, data, in_path.parent)
            content = r.render(type_, data)
            out_path.write_text(content, encoding="utf-8")
            print(f"[ok]  {type_:14s} → {out_path}")
            results.append((type_, out_path, True, None))
        except SystemExit as e:
            print(f"[err] {type_:14s} → {e}")
            results.append((type_, out_path, False, str(e)))
        except Exception as e:
            print(f"[err] {type_:14s} → {type(e).__name__}: {e}")
            results.append((type_, out_path, False, str(e)))

    total = len(results)
    ok = sum(1 for _, _, s, _ in results if s)
    print(f"\n=== Summary: {ok}/{total} succeeded ===")
    print(f"Output dir: {out_dir}")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
