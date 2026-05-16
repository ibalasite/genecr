# spec-basic review rules

You are reviewing `spec-basic.input.json`. spec-basic is THE root document —
everything downstream depends on it. Reject shallow or inconsistent content.

## Required checks

1. **competitors**: at least 6 entries; each entry's `highlight` must be a
   specific differentiator, not a vague placeholder like "亮點" or "TBD".
   Reject if any competitor field is `<...>` template noise.

2. **resource_counts**: every category value is a non-negative integer (or a
   nested dict whose leaves are non-negative integers). The set of categories
   must reflect ALL asset types the activity actually needs — if `summary`
   mentions music but `resource_counts.sounds` is missing, flag it.

3. **matrix vs axes**: every cell in `matrix` lies on the cross of an
   existing row in `axes.rows` and column in `axes.cols`. Flag dangling cells.

4. **user_journey vs wireframes**: every meaningful step in `user_journey`
   should have at least one `wireframes[]` entry that visualizes it. Flag
   journey steps with no wireframe coverage.

5. **i18n**: zh / en / es entries must be aligned — same keys present in all
   languages. Flag missing translations.

6. **acceptance_criteria**: each entry must be concrete and testable. Reject
   "system works", "good UX", etc. Must specify behavior + condition.

7. **internal references**: all cross-IDs (sc-xxx, api-xxx, ASSET-xxx) must
   resolve to something elsewhere in the document or be marked as upstream.

8. **template noise**: any field whose value matches `<...>` or "TBD" or
   "<填寫>" patterns. Reject — the AI generator did not fill it in.

## Issue category tags to use

- `shallow_competitor`, `count_inconsistent`, `dangling_matrix_cell`,
  `journey_no_wireframe`, `i18n_missing`, `untestable_acceptance`,
  `unresolved_reference`, `template_noise`
