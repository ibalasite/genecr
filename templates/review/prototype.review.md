# prototype review rules

You are reviewing `prototype.input.json`. The HTML must implement the
user_journey from spec-basic, use assets from the assets list, and reflect
the state machine from spec-advanced.

## Required checks

1. **HTML completeness**: `prototype_html` opens with `<html>` or
   `<!DOCTYPE` and contains both `<style>` and `<script>` blocks (single-
   file, zero external deps).

2. **user_journey coverage**: every step in `spec-basic.user_journey` is
   reachable via UI interaction in the HTML. Flag steps the HTML doesn't
   surface.

3. **asset references**: image / icon references in HTML use the same IDs
   or names as `assets.input.json`. No invented asset names.

4. **state machine**: state transitions in JS match
   `spec-advanced.client.states`. Flag transitions that don't exist
   upstream.

5. **mobile viewport**: 375px width target; check the CSS doesn't assume
   desktop layout.

6. **no external deps**: no `<script src="http...">`, no `<link
   rel="stylesheet" href="http...">`. All inline.

7. **interactivity**: every primary CTA has a click handler. Reject HTML
   that is purely static.

8. **template noise**: reject `<填寫>` / "TBD" in HTML strings.

## Issue category tags

- `not_complete_html`, `journey_step_unreachable`, `asset_id_invented`,
  `transition_not_upstream`, `not_mobile_375`, `external_dep_present`,
  `cta_no_handler`, `template_noise`
