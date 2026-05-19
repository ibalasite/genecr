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


def _attach_db_queries_to_tables(data: dict) -> dict:
    """For spec-advanced: map each db_queries[] entry to a data_models[] table
    via used_indexes (preferred) or SQL FROM/JOIN regex (fallback). Mutates
    each table dict with `_related_queries`; unmapped queries collected to
    `data["_orphan_queries"]`.
    """
    import re
    models = data.get("data_models") or []
    queries = data.get("db_queries") or []
    if not (models and queries):
        return data

    # Build index→table_name map
    idx_to_table: dict[str, str] = {}
    for m in models:
        for idx in (m.get("indexes") or []):
            if isinstance(idx, dict) and idx.get("name"):
                idx_to_table[idx["name"]] = m["name"]
            elif isinstance(idx, str):
                # string form like "INDEX foo (col)" — extract name
                mm = re.search(r"(?:INDEX|UNIQUE|PRIMARY\s+KEY)\s+`?(\w+)`?", idx)
                if mm:
                    idx_to_table[mm.group(1)] = m["name"]

    # Prepare buckets
    for m in models:
        m["_related_queries"] = []
    orphans: list = []

    for q in queries:
        target_tables: set[str] = set()
        # 1) used_indexes → table
        for idx_name in (q.get("used_indexes") or []):
            if idx_name in idx_to_table:
                target_tables.add(idx_to_table[idx_name])
        # 2) fallback: regex FROM/JOIN
        if not target_tables:
            sql = q.get("sql", "") or ""
            for m in models:
                if re.search(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+`?" + re.escape(m["name"]) + r"`?\b", sql, re.I):
                    target_tables.add(m["name"])
        if not target_tables:
            orphans.append(q)
            continue
        for m in models:
            if m["name"] in target_tables:
                m["_related_queries"].append(q)

    if orphans:
        data["_orphan_queries"] = orphans
    return data


def preprocess(type_: str, data: dict, base_dir: Path) -> dict:
    """Type-specific preprocessing.

    Step isolation rule: per-step preprocess must use ONLY that step's own data
    (no sibling-step file reads). spec-basic gets visual_total/audio_total
    as AI-self-reported integers in resource_counts (schema-required); assets
    derives summary from its own assets[] list. cross_check enforces the
    contract between the two.

    docs IS the aggregator — reading sibling .md and feature.json is its job.
    """
    if type_ == "spec-basic":
        rc = data.get("resource_counts", {}) or {}
        visual = int(rc.get("visual_total", 0) or 0)
        audio = int(rc.get("audio_total", 0) or 0)
        data["resource_summary"] = {
            "visual_total": visual,
            "audio_total": audio,
            "total": visual + audio,
        }
        return data
    if type_ == "assets":
        from collections import Counter
        counts = Counter(a.get("type") for a in (data.get("assets") or []))
        summary = {t: counts.get(t, 0) for t in ("image", "animation", "particle", "video", "font", "sound")}
        summary["visual_total"] = sum(summary[t] for t in ("image", "animation", "particle", "video", "font"))
        summary["audio_total"] = summary["sound"]
        summary["total"] = summary["visual_total"] + summary["audio_total"]
        data["resource_summary"] = summary
        return data
    if type_ == "spec-advanced":
        return _attach_db_queries_to_tables(data)
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
    # (separate template block). docs is the aggregator itself (no sibling .md).
    # Drop both from sections[] — neither has a .md to read.
    sections = [s for s in data.get("sections", [])
                if s.get("type") not in ("prototype", "docs")]
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

    # 把 mermaid.min.js 內嵌進 data，template 用 {{ mermaid_js | safe }}
    # 取代原本 docs.html.tmpl 用 CDN <script src="cdn.jsdelivr.net/..."> 的依賴
    # （違反 offline 原則，user 無網路或防火牆擋 CDN 時 mermaid 圖完全不渲染）。
    mermaid_js_path = TEMPLATES / "mermaid.min.js"
    data["mermaid_js"] = mermaid_js_path.read_text(encoding="utf-8") if mermaid_js_path.exists() else ""
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
