# prototype review rules

You review `prototype.input.json`. Apply each numbered rule. Cite the
real input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder.
Fail when: any string contains `<...>` / "TBD" inside `prototype_html`
or other fields.

### R2 — `not_complete_html`
Check: `prototype_html` starts with `<html`, `<!DOCTYPE`, `<body`, or
`<div` (case insensitive) AND contains both `<style>` and `<script>`.
Path: `prototype_html`
Fail when: missing any of those markers (per project rule: self-contained
inline CSS + JS).

### R3 — `external_dep_present`
Check: `prototype_html` contains no `src="http`, no `href="http` for
scripts/stylesheets.
Path: `prototype_html`
Fail when: any external URL reference for code or styles.

### R4 — `viewport_responsive_required`
Check: shell template sets `width=device-width`; `prototype_html` is free
to contain a phone frame (≤ 400px) AND/OR a desktop frame (≥ 1000px),
depending on the spec-basic.wireframes surfaces (player vs admin).
Path: `prototype_html`
Fail when: prototype_html declares its own viewport override that contradicts
device-width responsive layout.

### R5 — `journey_step_unreachable`
Check: every step in upstream `spec-basic.user_journey` is reachable
via a UI element (button / link / form) in `prototype_html`.
Path: `prototype_html` ↔ upstream `spec-basic.user_journey`
Fail when: a journey step has no visible UI handler.

### R6 — `asset_id_invented`
Check: when `prototype_html` references icon/image ids, they match ids
from upstream `assets.assets[].id`.
Path: `prototype_html` ↔ upstream `assets.assets[*].id`
Fail when: a referenced asset id is not declared upstream.

### R7 — `cta_no_handler`
Check: every primary action button has an `onclick` or event listener.
Path: `prototype_html`
Fail when: a `<button>` with no click handler.

### R8b — `prototype_layout_skeleton_missing`
Check: prototype_html MUST use the fixed layout skeleton — must contain all of:
`proto-page`, `proto-tabs`, `proto-surface` classes. AI doesn't get to
invent its own tab structure.
Path: `prototype_html`
Fail when: any of those three skeleton classes missing.
Fix hint: 照 prompt 提供的 skeleton 模板填內容；shell template 已有對應 CSS。

### R8c — `prototype_admin_surface_empty`
Check: if spec-basic has any admin wireframe (name 含「後台」/admin), the
`<div class="proto-surface" data-surface="admin">…</div>` block must contain
non-trivial demo content (not empty / not just whitespace).
Path: `prototype_html`
Fail when: admin surface is empty or contains < 5 chars of text.
Fix hint: 在 admin surface 內加入後台桌面 demo（玩家記錄表格、活動設定表單）。

### R8d — `prototype_help_steps_incomplete`
Check: proto-help `<ol><li>…</li></ol>` step count MUST equal
`len(spec-basic.user_journey) + len(spec-basic.admin_journey OR admin wireframes)`.
Path: `prototype_html` ↔ `spec-basic.user_journey` + `admin_journey`
Fail when: proto-help has fewer steps than the formula.
Fix hint: 補回缺少的 step — 每個 user_journey/admin_journey 條目各 1 步，不准取捨。

### R8 — `prototype_admin_uncovered`
Check: if `spec-basic.wireframes` contains any entry whose `name` includes
「後台」or `admin` (case-insensitive), `prototype_html` MUST contain a
matching admin demo block — at minimum the string「後台」or `admin`
appearing alongside a desktop-width layout container (≥ 1000px wide).
Path: `prototype_html` ↔ `spec-basic.wireframes[*].name`
Fail when: spec-basic has admin wireframe(s) but prototype_html has no
admin demo block.
Fix hint: 在 prototype_html 末尾加一個 `<div>` 桌面寬容器，顯示對應的後台 demo
（玩家記錄列表、活動設定面板等）。可用 tab 或上下並列方式跟玩家手機 demo 共存。

### R9a — `prototype_horizontal_overflow`
Check: prototype_html CSS must not cause horizontal scroll on the declared
viewport. Two anti-patterns:
1. Any rule with `width: 100%` + non-zero `padding` declared WITHOUT
   `box-sizing: border-box` (in that rule OR in a universal `* { ... }` reset)
   → content-box overflow.
2. `grid-template-columns: repeat(N, 1fr)` parent with child elements that have
   `min-width: Mpx` where N × M exceeds the parent's fixed pixel width.
Path: `prototype_html` (<style> blocks)
Fail when: either pattern present.
Fix hint: 在 <style> 頂部加 `*,*:before,*:after { box-sizing: border-box }`;
或 grid 改用 `repeat(N, minmax(0, 1fr))` 並刪掉 child 的 min-width。

### R9b — `prototype_dead_nav_item`
Check: every `<a>` nav element with disabled-looking style (inline
`opacity` < 0.7, `cursor: default`, `aria-disabled`, or class containing
`disabled`) MUST also have a functional handler — `onclick`, real `href`
(not `#` / empty), or `data-page` / `data-pane` / `data-tab` / `data-surface`.
Path: `prototype_html`
Fail when: an `<a>` looks disabled but is non-functional → fake nav item.
Fix hint: 要嘛實作該頁面、給它 onclick + 對應 pane；要嘛從 nav 移除別假裝有。

### R9c — `prototype_button_no_handler`
Check: every `<button id="X">` (non-`disabled`) without an `onclick` attribute
MUST have its id referenced in some inline `<script>` (e.g., via
`getElementById('X')`, `querySelector('#X')`, or any quoted occurrence of `X`).
Path: `prototype_html`
Fail when: a button with an id has no onclick and id never appears in scripts.
Fix hint: 加 onclick 或在 script 中 `document.getElementById('X').addEventListener(...)`。

### R9d — `prototype_default_open_modal`
Check: any CSS rule whose selector contains `modal` / `popup` / `overlay`
and declares `position: fixed` MUST default to `display: none`. State modifiers
(`.modal.show`, `.modal-mask.on` etc.) handle the open state.
Path: `prototype_html` (<style> blocks)
Fail when: a modal/overlay base rule has `display: block` / `flex` / `grid`
by default → covers page on load and blocks underlying nav.
Fix hint: base rule 改 `display: none`，再加 `.modal.show { display: flex; }`
之類由 user click 觸發的 modifier。

### R9e — `prototype_admin_responsive_break`
Check: admin-scoped CSS rules (selector matches `adm-*` / `dash-*` / `dashboard*`)
with `width: Npx` where N > 412 (mobile breakpoint) MUST be wrapped in a
`@media (min-width: ...)` guard.
Path: `prototype_html` (<style> blocks)
Fail when: admin rule has fixed width > 412px outside any @media min-width guard
→ admin layout overflows mobile viewport.
Fix hint: 包進 `@media (min-width: 768px) { ... }`；或改 `max-width` + `width: 100%`。

### R9f — `prototype_browser_overflow`
Check: rendered browser (headless chromium via Playwright) detected an
element where `scrollWidth > clientWidth + 2` — i.e., real horizontal
layout overflow that the browser layout engine actually exhibits, NOT
just static text-pattern analysis. Common cause: `grid-template-columns:
repeat(N, 1fr)` cells with `aspect-ratio` but no `min-width: 0`, so
auto-sizing makes cells exceed track width.
Path: `prototype_html` (rendered)
Fail when: any element overflows; especially serious when the parent
`overflow-x: hidden` clips the result (CLIPPED note in detail).
Fix hint: 在 grid item 加 `min-width: 0`（aspect-ratio + 1fr 必須一起加）;
或 grid 改 `repeat(N, minmax(0, 1fr))`；或縮減 cell 內容/padding/gap。

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `not_complete_html`
- `external_dep_present`
- `viewport_responsive_required`
- `journey_step_unreachable`
- `asset_id_invented`
- `cta_no_handler`
- `prototype_admin_uncovered`
- `prototype_layout_skeleton_missing`
- `prototype_admin_surface_empty`
- `prototype_help_steps_incomplete`
- `prototype_horizontal_overflow`
- `prototype_dead_nav_item`
- `prototype_button_no_handler`
- `prototype_default_open_modal`
- `prototype_admin_responsive_break`
- `prototype_browser_overflow`
