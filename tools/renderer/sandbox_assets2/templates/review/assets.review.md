# assets review rules

You review `assets.input.json`. Apply each numbered rule. Cite the real
input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder string.
Fail when: any string field equals or contains `<...>` / "TBD".

### R2 — `type_not_in_vocabulary`
Check: every `assets[].type` ∈ {image, animation, sound, video, font, particle}。
**只 6 種**：UI 實作要打包進 build 的素材檔。
Path: `assets[*].type`
Fail when:
- type 是 copywriting / i18n_strings（文案屬 spec-basic.i18n，企畫寫的，不重複放這）
- type 是 modules / acceptance_criteria / fields / competitors / axes / matrix_* /
  user_journey_steps / ui_sections / wireframes / timeline_phases / help_* /
  change_log / related_docs 等 spec 結構欄位（不是素材）
- 任何其他不在 6 種白名單的值
Fix hint: 刪除該 entry — 它本就不屬於 assets 範圍。文案改去 spec-basic.i18n，結構欄位本就在 spec-basic。

### R3 — `id_collision`
Check: `assets[].id` is unique across the list.
Path: `assets[*].id`
Fail when: two or more assets share the same id.

### R4 — `id_placeholder`
Check: `assets[].id` is meaningful (not `asset1`, `asset2`, `tbd`, `<id>`).
Path: `assets[*].id`
Fail when: id matches one of those generic patterns.

### R5 — `prompt_too_shallow`
Check: for visual asset types (image, animation, particle), the
`production_prompt` field contains at least 3 distinct concepts (subject,
style, composition or equivalent).
Path: `assets[*].production_prompt`
Fail when: prompt is one word, empty, or pure template placeholder.

### R6 — `usage_vague`
Check: `usage` specifies the scene + UI section + intended placement.
Path: `assets[*].usage`
Fail when: usage is a single word or generic phrase ("for the feature").

### R7 — `reference_placeholder`
Check: when `reference` is provided as a URL, it looks like a real URL
(starts with http:// or https://, contains a domain).
Path: `assets[*].reference`
Fail when: value is `<連結>` / `TBD` / empty string.

### R8 — `missing_owner_role`
Check: 每個 asset 必須有 `owner_role` ∈ {server_engineer | client_engineer | planner | po | art}。
Path: `assets[*].owner_role`
Fail when: 欄位缺失或值不在 enum。
Fix hint: 依 type 對照 — image/animation/sound/video/font/particle → art；copywriting/i18n → planner；API mock → server_engineer；UI sample → client_engineer；驗收附件 → po。

### R9 — `missing_output_format`
Check: 每個 asset 的 `output_format` 必須具體（含格式 + 解析度/位元率）。
Path: `assets[*].output_format`
Fail when: 缺、空、或只寫類型（如「圖片」「音效」）沒寫規格數字。
Fix hint: 寫成 `PNG 1920x600 @2x` / `MP3 44.1kHz stereo` / `MP4 H.264 720p 30fps` 等。

### R10 — `missing_suggested_filename`
Check: 每個 asset 的 `suggested_filename` 必須是合法 snake_case 檔名含副檔名。
Path: `assets[*].suggested_filename`
Fail when: 缺、含中文、含空白、無副檔名、或不含 feature_slug 前綴。
Fix hint: 寫成 `checkin7_banner_main.png` 這種格式。

### R11 — `usage_too_brief`
Check: `usage` 至少 20 字元且寫清 where（哪個畫面）/ when（什麼時機）/ what for（用途）。
Path: `assets[*].usage`
Fail when: 少於 20 字元或只是名詞短語沒寫使用情境。
Fix hint: 補上「在 X 畫面、Y 時機、用於 Z」三個 W。

### R12 — `category_not_in_spec_basic`
Check: 每個 asset 的 `category` 必須對應 `spec-basic.resource_counts[type]` 的某個子類 key。
Path: `assets[*].category` ↔ upstream `spec-basic.resource_counts.<type>.*`
Fail when: category 值不在 spec-basic 該 type 的子類列表中。
Fix hint: 對齊上游子類命名，不要自創新子類。

### R_sb_contract — `assets_visual_total_mismatch` / `assets_audio_total_mismatch`
Check: Counter(assets[].type) 各類加總必須符合 sb.resource_counts.visual_total / audio_total。
Path: `assets[*].type` ↔ `<spec-basic upstream>.resource_counts.{visual_total, audio_total}`
Fail when: 加總不符（美術 = image+animation+particle+video+font；音效 = sound）。
Fix hint: 補/減 assets 項目，或請 spec-basic 修 totals（取決於哪邊正確）。

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `type_not_in_vocabulary`
- `id_collision`
- `id_placeholder`
- `prompt_too_shallow`
- `usage_vague`
- `reference_placeholder`
- `missing_owner_role`
- `missing_output_format`
- `missing_suggested_filename`
- `usage_too_brief`
- `category_not_in_spec_basic`
- `assets_visual_total_mismatch`
- `assets_audio_total_mismatch`
