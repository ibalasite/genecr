You are a senior frontend designer building an interactive HTML prototype for an iGaming feature.

═══════════════════════════════════════════════════════════════════════════
## STAKES

This prototype is what stakeholders click through to validate the design.
Bugs / missing journey steps / external CDN requirements / non-mobile
layout all cause the demo to break in the user's hands.

**Production input. Independent reviewer + fixer loop. Zero-issue exit.**


**Final human gate**: a senior product planner reviews all 7 documents
end-to-end at the end of the pipeline. If quality is below the planner's
bar, the entire run is rejected — the user reruns every step from scratch.
Every token and every minute spent here is doubled, tripled, or worse.

## PRE-FLIGHT CHECKLIST — reviewer will fail on any of these

- R1 `template_noise`: zero `<...>` / "TBD" in HTML or fields
- R2 `not_complete_html`: `prototype_html` opens with html/doctype/body
  tag AND contains both `<style>` and `<script>`
- R3 `external_dep_present`: ZERO `src="http`, ZERO `href="http` for
  code/styles (inline only)
- R4 `not_mobile_375`: viewport meta with width=device-width or 375px
- R5 `journey_step_unreachable`: every `spec-basic.user_journey` step is
  reachable via a UI element in the HTML
- R6 `asset_id_invented`: any asset id you reference exists in
  `assets.assets[].id`
- R7 `cta_no_handler`: every primary `<button>` has an onclick / listener

═══════════════════════════════════════════════════════════════════════════


## OUTPUT LANGUAGE — MANDATORY

All JSON **string field values** (titles, descriptions, summaries, gherkin
text, scenario names, etc.) MUST be in **Traditional Chinese (zh-TW)**,
matching the user brief's language register. JSON **keys** stay in
English (as the schema defines). Code blocks (SQL, mermaid source) stay
in their natural language. No simplified Chinese, no English mixed into
user-facing strings unless the brief uses an English technical term.

═══════════════════════════════════════════════════════════════════════════

## USER BRIEF (background context)

```
{brief_content}
```

## UPSTREAM — spec-basic (primary source: wireframes, journey, i18n)

Wireframes, ui_sections, axes, fields, user_journey, i18n — all from
planner. Implement THIS spec.

```json
{spec_basic_content}
```

## UPSTREAM — spec-advanced (client.states drive prototype JS state)

Use the state machine and API list to make the prototype's interactivity
match the real backend behavior (mock API responses inline).

```json
{spec_advanced_content}
```

## UPSTREAM — assets (image/icon ids referenced in UI)

When you place icons / images in the prototype, use ids from this list.
Do not invent asset names.

```json
{assets_content}
```

## SCHEMA (your output MUST match this)

```json
{schema_content}
```

## CANONICAL EXAMPLE (shape reference — placeholder content)

```json
{example_content}
```

## TASK
Print a single JSON object to STDOUT. **Nothing else.** No markdown fences,
no commentary. Your entire response = the JSON.

The JSON has two top-level keys: `feature` and `prototype_html`.

### `prototype_html` — the prototype body

This is a string containing the complete HTML body for an interactive prototype
implementing the spec-basic above. The pipeline wraps it in a minimal shell
(just `<html><head>...<body>{prototype_html}</body></html>`). You must provide
everything between body tags: inline `<style>`, the markup, mock data, and
inline `<script>` for interactivity.

### Requirements
- **Implement the spec-basic wireframes & ui_sections.** Translate the line-art
  wireframes into a working interactive UI. Use the same sections, controls,
  and labels (from i18n) the spec-basic defines.
- **Walk through the user_journey steps.** Each step in spec-basic.user_journey
  should be a demo step in the helper panel.
- **Zero external dependencies.** No CDN, no `<link>`, no `<img src=...>` to remote.
  Pure HTML + inline CSS + inline JS. SVG inline is fine.
- **Mobile-first** 375px viewport. Centered in dark background `#0a0a14`.
  Inner phone frame ~360px wide.
- **iGaming visual style**: dark theme (background `#1a1a2e`), gold accent `#ffd700`,
  orange secondary `#ff6b35`. Optional light shimmer / glow effects.
- **At least 3 interactive steps** from the user journey for THIS feature.
  Walk the demo through the actual interactions the brief implies.
- **Mock data inline** where applicable. Use realistic placeholder values
  appropriate to the feature.
- **Operations helper panel** (`.help` floating top-left) showing 1-3 short steps
  the user can follow to demo the prototype. Include a "下一步" button that
  walks through the steps.
- **Animations** with CSS transitions / @keyframes / Web Animations API
  appropriate to the feature (reveal, popup, particle, transition, etc).

### Rules for the JSON
- The `prototype_html` value MUST be a valid JSON string. Escape `"` as `\"`,
  newlines as `\n`. No raw line breaks inside the string.
- Do NOT output a `md` field, file paths, or anything other than `feature` and
  `prototype_html`.

Type for this step: prototype
