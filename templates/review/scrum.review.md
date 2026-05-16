# scrum review rules

You review `scrum.input.json`. Apply each numbered rule. Cite the real
input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder.
Fail when: any string contains `<...>` / "TBD".

### R2 — `module_uncovered`
Check: every distinct user_journey area in `spec-basic.user_journey` has
at least one story.
Path: `stories[*]` ↔ upstream `spec-basic.user_journey`
Fail when: a user_journey area has no representative story.

### R3 — `table_no_story`
Check: every entry in `spec-advanced.data_models[]` is referenced by at
least one backend story.
Path: `stories[*]` ↔ upstream `spec-advanced.data_models`
Fail when: a table has no story creating/maintaining/querying it.

### R4 — `role_placeholder`
Check: each story's `role`, `want`, `benefit` is concrete (not "<role>").
Path: `stories[*].{role, want, benefit}`
Fail when: placeholder text or empty.

### R5 — `orphan_group`
Check: every `stories[].group` value matches an existing `groups[].key`.
Path: `stories[*].group` ↔ `groups[*].key`
Fail when: a story references an undefined group key.

### R6 — `non_fibonacci_points`
Check: when `points` is provided, it is in {1, 2, 3, 5, 8, 13}.
Path: `stories[*].points`
Fail when: non-Fibonacci or non-integer value (e.g. 42, 100, "TBD").

### R7 — `dangling_dependency`
Check: every `stories[].depends_on` id matches another `stories[].id`.
Path: `stories[*].depends_on`
Fail when: a dependency id is not declared.

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `module_uncovered`
- `table_no_story`
- `role_placeholder`
- `orphan_group`
- `non_fibonacci_points`
- `dangling_dependency`
