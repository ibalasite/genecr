# prototype review rules

You review `prototype.input.json`. Apply each numbered rule. Cite the
real input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder.
Fail when: any string contains `<...>` / "TBD" inside `prototype_html`
or other fields.

### R2 — `not_complete_html`
Check: `prototype_html` starts with `<html`, `<!DOCTYPE`, `<body`, or
`<div` (case insensitive) AND contains both `<style>` and `<script>`.
Path: `prototype_html`
Fail when: missing any of those markers (per project rule: self-contained
inline CSS + JS).

### R3 — `external_dep_present`
Check: `prototype_html` contains no `src="http`, no `href="http` for
scripts/stylesheets.
Path: `prototype_html`
Fail when: any external URL reference for code or styles.

### R4 — `not_mobile_375`
Check: `prototype_html` references mobile viewport (`width=device-width`
or explicit 375px).
Path: `prototype_html`
Fail when: viewport meta missing or width clearly desktop-only.

### R5 — `journey_step_unreachable`
Check: every step in upstream `spec-basic.user_journey` is reachable
via a UI element (button / link / form) in `prototype_html`.
Path: `prototype_html` ↔ upstream `spec-basic.user_journey`
Fail when: a journey step has no visible UI handler.

### R6 — `asset_id_invented`
Check: when `prototype_html` references icon/image ids, they match ids
from upstream `assets.assets[].id`.
Path: `prototype_html` ↔ upstream `assets.assets[*].id`
Fail when: a referenced asset id is not declared upstream.

### R7 — `cta_no_handler`
Check: every primary action button has an `onclick` or event listener.
Path: `prototype_html`
Fail when: a `<button>` with no click handler.

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `not_complete_html`
- `external_dep_present`
- `not_mobile_375`
- `journey_step_unreachable`
- `asset_id_invented`
- `cta_no_handler`
