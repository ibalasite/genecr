#!/usr/bin/env python3
"""
GeneCR renderer — template + JSON input → output file.

Usage:
    python render.py <type> <input.json> <output_path>

Types: spec-basic | spec-advanced | assets | bdd | scrum | docs | prototype

Templates live at <repo_root>/templates/
Schemas live at  <repo_root>/templates/schemas/
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, ChainableUndefined

try:
    from jsonschema import validate as _validate
    from jsonschema import ValidationError
except ImportError:
    _validate = None

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "templates"
SCHEMAS = REPO_ROOT / "templates" / "schemas"

TYPE_TO_FILENAME = {
    "spec-basic":    "spec-basic.md.tmpl",
    "spec-advanced": "spec-advanced.md.tmpl",
    "assets":        "assets.md.tmpl",
    "bdd":           "bdd.md.tmpl",
    "scrum":         "scrum.md.tmpl",
    "docs":          "docs.html.tmpl",
    "prototype":     "prototype.html.tmpl",
}


def load_input(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_input(type_: str, data: dict) -> None:
    schema_path = SCHEMAS / f"{type_}.schema.json"
    if not schema_path.exists():
        return
    if _validate is None:
        print(f"[warn] jsonschema not installed; skipping validation", file=sys.stderr)
        return
    with schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)
    try:
        _validate(instance=data, schema=schema)
    except ValidationError as e:
        print(f"[error] {type_} input failed schema validation:\n  {e.message}\n  at: {list(e.absolute_path)}", file=sys.stderr)
        sys.exit(2)


def preprocess(type_: str, data: dict, base_dir: Path) -> dict:
    """Type-specific preprocessing. For 'docs', read .md files into HTML chunks.
    Section filenames are derived from feature.slug + section.type — AI does not
    control filenames. AI provides {title, type} per section; we compute md.
    """
    if type_ != "docs":
        return data
    import markdown as _md
    # Resolve slug from sibling feature.json (pipeline-controlled, not AI)
    feature_file = base_dir / "feature.json"
    slug = ""
    if feature_file.exists():
        try:
            slug = json.loads(feature_file.read_text(encoding="utf-8")).get("slug", "")
        except Exception:
            pass
    # Prototype path also derived from slug (pipeline-controlled, not AI)
    if slug:
        data["prototype_path"] = f"{slug}-prototype.html"
    md = _md.Markdown(extensions=["fenced_code", "tables", "toc", "attr_list"])
    # prototype is rendered as standalone .html and embedded via prototype_path
    # (separate template block). Drop any prototype entry the AI included in
    # sections[] — there is no sibling .md to read.
    sections = [s for s in data.get("sections", [])
                if s.get("type") != "prototype"]
    data["sections"] = sections
    for s in sections:
        # Compute md filename deterministically: <slug>-<type>.md
        if "type" in s and slug:
            s["md"] = f"{slug}-{s['type']}.md"
        if "md" not in s:
            raise SystemExit(f"docs section missing both 'type' and 'md': {s}")
        md_path = (base_dir / s["md"]).resolve()
        if not md_path.exists():
            raise SystemExit(f"docs section missing file: {md_path}")
        raw = md_path.read_text(encoding="utf-8")
        md.reset()
        s["html"] = md.convert(raw)
    return data


def render(type_: str, data: dict) -> str:
    if type_ not in TYPE_TO_FILENAME:
        raise SystemExit(f"unknown type: {type_}. valid: {', '.join(TYPE_TO_FILENAME)}")
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        undefined=ChainableUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    tmpl = env.get_template(TYPE_TO_FILENAME[type_])
    return tmpl.render(**data)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 1
    _, type_, input_path, output_path = argv
    in_path = Path(input_path)
    data = load_input(in_path)
    validate_input(type_, data)
    data = preprocess(type_, data, in_path.parent)
    result = render(type_, data)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result, encoding="utf-8")
    print(f"[ok] {type_} → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
