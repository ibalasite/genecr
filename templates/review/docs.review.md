# docs review rules

You are reviewing `docs.input.json`. This is the integration document
center — sections reference the 6 upstream .md files. Internal links must
resolve. API Explorer config must match spec-advanced APIs.

## Required checks

1. **section coverage**: `sections[]` contains entries for spec-basic,
   spec-advanced, assets, bdd, scrum, prototype (the 6 core docs). Missing
   any → flag.

2. **section types**: every `sections[].type` matches one of the 7 step
   types (spec-basic / spec-advanced / assets / bdd / scrum / prototype /
   docs). No invented types.

3. **api_explorer ↔ spec-advanced**: every entry in `api_explorer[]` has
   a matching entry in `spec-advanced.apis` with the same id, method, path.
   Flag inventions or divergences.

4. **api_explorer completeness**: each entry has method, path, desc,
   plus at least one `responses[]` example payload.

5. **feature consistency**: `feature.name` and `feature.slug` match
   spec-basic.feature exactly.

6. **template noise**: reject `<...>` placeholders.

## Issue category tags

- `section_missing`, `section_invented_type`, `api_explorer_not_in_specs`,
  `api_explorer_response_empty`, `feature_inconsistent`, `template_noise`
