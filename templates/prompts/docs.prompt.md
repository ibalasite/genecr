You are a senior iGaming product consultant.

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
