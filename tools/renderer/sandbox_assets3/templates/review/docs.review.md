# docs review rules

You review `docs.input.json`. Apply each numbered rule. Cite the real
input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder.
Fail when: any string contains `<...>` / "TBD".

### R2 — `section_missing`
Check: `sections[]` includes entries for at least: spec-basic,
spec-advanced, assets, bdd, scrum, prototype.
Path: `sections[*].type`
Fail when: any of those 6 types is absent from sections.

### R3 — `section_invented_type`
Check: every `sections[].type` is one of: spec-basic, spec-advanced,
assets, bdd, scrum, prototype, docs.
Path: `sections[*].type`
Fail when: type value is not in that set.

### R4 — `api_explorer_not_in_specs`
Check: every entry in `api_explorer[]` has matching id+method+path in
upstream `spec-advanced.apis[]`.
Path: `api_explorer[*]` ↔ upstream `spec-advanced.apis[*]`
Fail when: id/method/path triple does not match any upstream API.

### R5 — `api_explorer_response_empty`
Check: each `api_explorer[].responses` (if the field is declared) has
at least one example payload.
Path: `api_explorer[*].responses`
Fail when: responses array is empty.

### R6 — `feature_inconsistent`
Check: `feature.name` and `feature.slug` exactly match
`spec-basic.feature.name` / `spec-basic.feature.slug`.
Path: `feature` ↔ upstream `spec-basic.feature`
Fail when: name or slug differs.

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `section_missing`
- `section_invented_type`
- `api_explorer_not_in_specs`
- `api_explorer_response_empty`
- `feature_inconsistent`
