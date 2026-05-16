# assets review rules

You review `assets.input.json`. Apply each numbered rule. Cite the real
input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder string.
Fail when: any string field equals or contains `<...>` / "TBD".

### R2 — `type_not_in_vocabulary`
Check: every `assets[].type` matches a category key declared in
`spec-basic.resource_counts` (case-insensitive, singular/plural tolerated).
Path: `assets[*].type` ↔ upstream `resource_counts.*`
Fail when: an asset's type has no matching upstream category.

### R3 — `id_collision`
Check: `assets[].id` is unique across the list.
Path: `assets[*].id`
Fail when: two or more assets share the same id.

### R4 — `id_placeholder`
Check: `assets[].id` is meaningful (not `asset1`, `asset2`, `tbd`, `<id>`).
Path: `assets[*].id`
Fail when: id matches one of those generic patterns.

### R5 — `prompt_too_shallow`
Check: for visual asset types (image, animation, particle), the
`image_prompt` field contains at least 3 distinct concepts (subject,
style, composition or equivalent).
Path: `assets[*].image_prompt`
Fail when: prompt is one word, empty, or pure template placeholder.

### R6 — `usage_vague`
Check: `usage` specifies the scene + UI section + intended placement.
Path: `assets[*].usage`
Fail when: usage is a single word or generic phrase ("for the feature").

### R7 — `reference_placeholder`
Check: when `reference` is provided as a URL, it looks like a real URL
(starts with http:// or https://, contains a domain).
Path: `assets[*].reference`
Fail when: value is `<連結>` / `TBD` / empty string.

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `type_not_in_vocabulary`
- `id_collision`
- `id_placeholder`
- `prompt_too_shallow`
- `usage_vague`
- `reference_placeholder`
