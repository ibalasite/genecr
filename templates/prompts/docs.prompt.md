You are a senior iGaming product consultant.

═══════════════════════════════════════════════════════════════════════════
## STAKES

`docs.input.json` is the final integration document. It pulls all 6
upstream docs into the document center + API explorer. Wrong section
type → broken page. Invented API in api_explorer → live "试 API" button
hits nothing.

**Production input. Independent reviewer + fixer loop. Zero-issue exit.**

## PRE-FLIGHT CHECKLIST — reviewer will fail on any of these

- R1 `template_noise`: zero `<...>` / "TBD"
- R2 `section_missing`: `sections[]` covers all 6 step types
- R3 `section_invented_type`: every `sections[].type` is in
  {spec-basic, spec-advanced, assets, bdd, scrum, prototype, docs}
- R4 `api_explorer_not_in_specs`: every api_explorer entry has matching
  id+method+path in upstream `spec-advanced.apis[]`
- R5 `api_explorer_response_empty`: each api_explorer responses has at
  least one example
- R6 `feature_inconsistent`: `feature.name`/`feature.slug` exactly match
  upstream `spec-basic.feature`

═══════════════════════════════════════════════════════════════════════════


## OUTPUT LANGUAGE — MANDATORY

All JSON **string field values** (titles, descriptions, summaries, gherkin
text, scenario names, etc.) MUST be in **Traditional Chinese (zh-TW)**,
matching the user brief's language register. JSON **keys** stay in
English (as the schema defines). Code blocks (SQL, mermaid source) stay
in their natural language. No simplified Chinese, no English mixed into
user-facing strings unless the brief uses an English technical term.

═══════════════════════════════════════════════════════════════════════════

## USER BRIEF

```
{brief_content}
```

## UPSTREAM — all 6 prior step outputs

docs is the integration document — sections[] references the 6 core docs.
api_explorer[] entries MUST match `spec-advanced.apis` by id/method/path.

### spec-basic

```json
{spec_basic_content}
```

### spec-advanced

```json
{spec_advanced_content}
```

### assets

```json
{assets_content}
```

### bdd

```json
{bdd_content}
```

### scrum

```json
{scrum_content}
```

### prototype

```json
{prototype_content}
```

## SCHEMA (your output MUST match this)

```json
{schema_content}
```

## CANONICAL EXAMPLE (shape reference)

```json
{example_content}
```

## TASK
Print a single JSON object to STDOUT. **Nothing else.** No markdown fences,
no commentary. Your entire response = the JSON.

Rules:
- Use the user brief above for content (feature.name, summary, axes, fields, etc.).
- Match the schema shape exactly: every required top-level key present.
- Follow the canonical example for nested structure conventions.
- For competitor research, use industry knowledge (do not attempt to read files).
- All cross-reference IDs (api-xxx, sc-xxx, ASSET-xxx) must be self-consistent.

## FILENAMES — IMPORTANT
The pipeline computes all filenames from feature.slug. **Do NOT output any of**:
- `sections[].md` (use only `{"title", "type"}` per section)
- `prototype_path`
Valid `type` values: `spec-basic`, `spec-advanced`, `assets`, `bdd`, `scrum`.

Type for this step: docs
