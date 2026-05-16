# assets review rules

You are reviewing `assets.input.json`. The asset list must align EXACTLY
with `spec-basic.resource_counts`. The program cross_check verifies counts
mechanically; your job is qualitative review.

## Required checks

1. **type vocabulary**: every `assets[].type` matches a category declared
   in `spec-basic.resource_counts`. Flag types not in that vocabulary.

2. **naming**: `id` is unique across the list, kebab-case or ASSET-NNN
   format, semantically meaningful (no `asset1`, `asset2` placeholders).

3. **image_prompt quality**: for visual assets (image / animation /
   particle), `image_prompt` must specify subject + style + composition.
   Reject one-word prompts or pure template noise.

4. **usage clarity**: `usage` describes where the asset is used in product
   (which scene / which UI section), not just "for the feature".

5. **reference resolution**: if `reference.url` is provided, it should be
   a plausible URL (not `<連結>`).

6. **template noise**: any `<...>` placeholder fields.

## Issue category tags

- `type_not_in_vocabulary`, `id_collision`, `id_placeholder`,
  `prompt_too_shallow`, `usage_vague`, `reference_placeholder`,
  `template_noise`
