# bdd review rules

You review `bdd.input.json`. Apply each numbered rule. Cite the real
input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder.
Fail when: any string contains `<...>` / "TBD".

### R2 — `sequence_diagram_missing`
Check: every entry in `scenarios[]` has a non-empty `sequence_diagram`.
Path: `scenarios[*].sequence_diagram`
Fail when: field missing, empty, or null. **Critical (user-flagged).**

### R3 — `sequence_diagram_invalid_mermaid`
Check: `sequence_diagram` starts with `sequenceDiagram` keyword.
Path: `scenarios[*].sequence_diagram`
Fail when: text doesn't begin with `sequenceDiagram` (after optional
whitespace).

### R4 — `gherkin_incomplete`
Check: `gherkin_zh` (or `gherkin_en`) contains Given / When / Then (or
中文 假設/當/那麼).
Path: `scenarios[*].gherkin_zh`
Fail when: any of the three steps is missing.

### R5 — `api_undeclared`
Check: every API id referenced in `scenarios[*].apis` exists in upstream
`spec-advanced.apis[*].id`.
Path: `scenarios[*].apis` ↔ upstream `spec-advanced.apis[*].id`
Fail when: a referenced API id is not declared upstream.

### R6 — `acceptance_uncovered`
Check: every `spec-basic.rules` (or `acceptance_criteria`) entry is
addressed by at least one scenario's Then step.
Path: scenarios collectively ↔ upstream `spec-basic.rules`
Fail when: an acceptance criterion has no scenario covering it.

### R7 — `count_inconsistent`
Check: number of scenarios ≥ upstream `spec-basic.resource_counts.acceptance_criteria` + upstream `spec-advanced.counts.api_endpoints` (if both present).
Path: `scenarios` length
Fail when: insufficient scenarios for declared coverage need.

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `sequence_diagram_missing`
- `sequence_diagram_invalid_mermaid`
- `gherkin_incomplete`
- `api_undeclared`
- `acceptance_uncovered`
- `count_inconsistent`
