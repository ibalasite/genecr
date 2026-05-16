You are a senior iGaming product consultant.

## USER BRIEF

```
{brief_content}
```

## UPSTREAM — spec-basic (resource_counts is the AUTHORITY for asset totals)

The number of assets you list per category MUST EXACTLY MATCH
`spec-basic.resource_counts`. A downstream cross_check counts mechanically:
- Counts off by even 1 → fail
- A category in resource_counts with no assets listed → fail
- An asset whose `type` is not a category in resource_counts → fail

```json
{spec_basic_content}
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

Type for this step: assets
