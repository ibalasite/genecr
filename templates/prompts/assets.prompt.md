You are a senior iGaming product consultant.

═══════════════════════════════════════════════════════════════════════════
## STAKES

`spec-basic.resource_counts` is the CONTRACT for asset totals. Your
output is verified by a program cross_check — counts off by even 1 will
fail the loop. Sloppy = guaranteed rework.

**Production input. Independent reviewer + fixer loop. Zero-issue exit.**


**Final human gate**: a senior product planner reviews all 7 documents
end-to-end at the end of the pipeline. If quality is below the planner's
bar, the entire run is rejected — the user reruns every step from scratch.
Every token and every minute spent here is doubled, tripled, or worse.

## PRE-FLIGHT CHECKLIST — reviewer will fail on any of these

- R1 `template_noise`: zero `<...>` / "TBD"
- R2 `type_not_in_vocabulary`: every `assets[].type` matches a category
  key in upstream `spec-basic.resource_counts`
- R3 `id_collision`: `assets[].id` is unique
- R4 `id_placeholder`: ids are meaningful (no asset1 / asset2 / tbd)
- R5 `prompt_too_shallow`: visual assets have image_prompt with subject +
  style + composition (≥ 3 concepts)
- R6 `usage_vague`: usage specifies scene + UI section + placement
- R7 `reference_placeholder`: reference URL is a real URL or omitted

**HARD COUNT RULE**: total assets per category in your output MUST equal
the integer in `spec-basic.resource_counts.<category>` (case-insensitive,
singular/plural normalized by program). If spec-basic says images=20, you
output exactly 20 image-type entries. Period.

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

## UPSTREAM — spec-basic (resource_counts is the AUTHORITY for asset totals)

The number of assets you list per category MUST EXACTLY MATCH
`spec-basic.resource_counts`. A downstream cross_check counts mechanically:
- Counts off by even 1 → fail
- A category in resource_counts with no assets listed → fail
- An asset whose `type` is not a category in resource_counts → fail
- `Counter(assets[].type)` 美術類（image+animation+particle+video+font）加總必須 == upstream `spec-basic.resource_counts.visual_total`；`sound` 加總必須 == `audio_total`。違反會被 cross_check 擋下（`assets_visual_total_mismatch` / `assets_audio_total_mismatch`）。

```json
{spec_basic_content}
```

## 每個 asset 必填欄位（reviewer R8-R12 強制）

```
id              # ASSET-NNN 或 kebab-case 唯一 id
name            # 中文描述名（如「文案-連簽 7 日領大獎」）
type            # ★ ENUM 限定 6 種：image / animation / sound / video / font / particle
                #   = UI 實作要打包進 build 的素材檔。**只此 6 種**，schema enum 擋
                #   **禁列**：copywriting / i18n_strings（文案屬 spec-basic.i18n）
                #            / modules / acceptance_criteria / fields / wireframes 等
                #            spec 結構欄位（描述用，不是素材）
category        # ★ 子類，必須對應 spec-basic.resource_counts[type] 的某個 key
                #   例如 spec-basic 寫 image.格子狀態圖=21，這 21 張的 category 都填「格子狀態圖」
owner_role      # ★ scrum team role 之一: server_engineer | client_engineer | planner | po | art
output_format   # ★ 含格式 + 解析度/位元率，例如:
                #   image:  "PNG 1920x600 @2x"
                #   sound:  "MP3 44.1kHz stereo, ≤200KB"
                #   animation: "JSON Lottie ≤60KB"
                #   video:  "MP4 H.264 720p 30fps"
                #   font:   "WOFF2"
                #   copywriting / i18n_strings: "JSON i18n key-value"
suggested_filename  # ★ snake_case + 副檔名，含 feature_slug 前綴
                    #   例如「checkin7_banner_main.png」「checkin7_sfx_claim_success.mp3」
usage           # ★ ≥20 字，寫清 where（哪畫面）/ when（什麼時機）/ what for（用途）
spec            # 字串陣列（推薦）或字串。一行一條規格。例如 ["主視覺橫幅", "支援 zh/en/es 三語文字疊圖"]
production_prompt  # ★ 全類型必填，≥ 15 字。給 AI / 美術產出這資源的指引（統一一欄，不分類型）
                #   image / animation / particle / video：建議英文 T2I/T2V prompt 含 subject + style + composition
                #   sound：寫音色 + 長度 + 情境，例「short upbeat coin-collect chime, 0.8s, bright synth」
                #   font：寫字型風格 + 字重 + 字符集需求，例「圓潤無襯線繁中字型, Bold, 數字 0-9 + 常用 1000 字」
image_prompt    # （legacy / 可選）視覺類英文 prompt — 若已寫在 production_prompt 內可省略
```

**owner_role 對照表**（所有 6 種素材都歸 art — 同一角色用 AI 或手作）：
- `image` / `animation` / `sound` / `video` / `font` / `particle` → **art**

(其他角色 server / client / planner / po 在這 step 不應出現，他們的工作在 scrum stories 而非 assets)

**category 規則**：上游 spec-basic.resource_counts 拆了哪些子類，這些 assets 的
category 就必須是其中一個 key（reviewer R12 強制）。不可自創新子類，要新增請改 spec-basic。

**數字對齊**：每個 `<type>.<category>` 的 spec 宣告數 = 你列出的該 category assets 數。
程式 cross_check 會逐子類比對，不一致 fixer 必補。

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
