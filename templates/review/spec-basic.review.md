# spec-basic review rules

You review `spec-basic.input.json`. Apply each numbered rule. Cite the
real input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder string.
Fail when: any string field equals or contains `<...>` / "TBD" / "<待補>" / "<填寫>".

### R2 — `shallow_competitor`
Check: every entry in `competitors[]` has all required sub-fields filled
with concrete content (no placeholders, no one-word answers).
Path: `competitors[*].{name, market, highlight, url}` plus any extended
fields (mechanic, rtp, payout, user_flow, differentiation, weakness) the
input declares.
Fail when: any sub-field is empty, a placeholder, or one word.

### R3 — `count_inconsistent`
Check: `resource_counts.<category>` integer equals the number of entries
in this document that match that category.
Path: `resource_counts.*`
Fail when: declared count != actual count of matching entries within this
document (e.g. resource_counts.competitors=6 but competitors[] has 5).
Note: cross-document counts are checked by program cross_check, not here.

### R4 — `axis_option_mismatch`
Check: `matrix.cols` values appear as `options[].name` in some axis;
`matrix.rows[].label` values appear as `options[].name` in some axis.
Path: `matrix.{cols, rows[].label}` ↔ `axes[*].options[*].name`
Fail when: matrix references a label that no axis option defines.

### R5 — `journey_no_wireframe`
Check: every meaningful step in `user_journey[]` is depicted by at least
one `wireframes[]` entry.
Path: `user_journey[*]` ↔ `wireframes[*]`
Fail when: a journey step has no wireframe that visualises it.

### R6 — `i18n_missing`
Check: every translation key referenced in `ui_sections`, `ui_misc`, or
`copywriting` (if present) exists in `i18n` for every declared language.
Path: `i18n.*`
Fail when: a referenced key is missing for any declared language.

### R7 — `untestable_acceptance`
Check: every entry in `rules[]` (or `acceptance_criteria[]` if present)
specifies a concrete condition + observable outcome.
Path: `rules[*]` / `acceptance_criteria[*]`
Fail when: text is purely abstract ("system works", "good UX"), or
specifies an outcome without the triggering condition.

### R8 — `unresolved_reference`
Check: every cross-ID (e.g. `api-xxx`, `sc-xxx`, `ASSET-xxx`) referenced
inside this document resolves to another item in this document, or to
an upstream document.
Path: any string that matches the ID patterns
Fail when: ID appears but no definition is found.

### R9 — `skeleton_with_text`
Check: `.wf-skeleton-line` / `.wf-skeleton-pill` / `.wf-skeleton-block`
must be **empty placeholders** (LOADING state) — never contain text
content. Wireframe DSL section 3.6 is explicit.
Path: `wireframes[*].html`
Fail when: regex `class="[^"]*wf-skeleton-(line|pill|block)[^"]*"[^>]*>\s*[^<\s]` matches (skeleton tag has text content between open/close).
Fix hint: replace `.wf-skeleton-line` with `.wf-line` (text line) or `.wf-text` (paragraph).

### R10 — `inline_children_no_row`
Check: `.wf-panel` may not contain `<span>` children directly — inline
items must be wrapped in `.wf-row` for horizontal layout.
Path: `wireframes[*].html`
Fail when: regex `<div[^>]*class="[^"]*wf-panel[^"]*"[^>]*>\s*<span` matches.
Fix hint: wrap the inline children in `<div class="wf-row">…</div>`.

### R11 — `class_not_in_dsl`
Check: every `wf-*` class used in wireframe HTML must be declared in
`templates/wireframe-dsl.md` section 3 (no self-invented classes).
Path: `wireframes[*].html`
Fail when: a wf-* class string is not on the DSL allow-list.
Fix hint: pick a real DSL primitive; do not invent classes.

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `shallow_competitor`
- `count_inconsistent`
- `axis_option_mismatch`
- `journey_no_wireframe`
- `i18n_missing`
- `untestable_acceptance`
- `unresolved_reference`
- `skeleton_with_text`
- `inline_children_no_row`
- `class_not_in_dsl`
