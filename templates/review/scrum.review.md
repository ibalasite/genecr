# scrum review rules

You are reviewing `scrum.input.json`. Stories must cover every spec-basic
module, every spec-advanced table, every asset type. Estimation must be
reasonable.

## Required checks

1. **module coverage**: every spec-basic `summary` / `user_journey` module
   has at least one story. Flag missing modules.

2. **table coverage**: every `spec-advanced.data_models[]` table has at
   least one backend story (creation, migration, or query workload).

3. **asset coverage**: every distinct asset type (per spec-basic
   resource_counts) has at least one art/sound story.

4. **story shape**: each story has role / want / benefit filled with
   concrete content, not "<role>" placeholder.

5. **group consistency**: every `stories[].group` references an existing
   `groups[].key`. No orphan group keys.

6. **estimation sanity**: `points` ∈ {1, 2, 3, 5, 8, 13} (Fibonacci). Flag
   42, 100, or non-numeric values.

7. **depends_on**: every dependency references an existing story id.

8. **template noise**: reject `<...>` placeholders.

## Issue category tags

- `module_uncovered`, `table_no_story`, `asset_type_no_story`,
  `role_placeholder`, `orphan_group`, `non_fibonacci_points`,
  `dangling_dependency`, `template_noise`
