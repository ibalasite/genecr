# scrum review rules

You review `scrum.input.json`. Apply each numbered rule. Cite the real
input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder.
Fail when: any string contains `<...>` / "TBD".

### R2 — `module_uncovered`
Check: every distinct user_journey area in `spec-basic.user_journey` has
at least one story.
Path: `stories[*]` ↔ upstream `spec-basic.user_journey`
Fail when: a user_journey area has no representative story.

### R3 — `table_no_story`
Check: every entry in `spec-advanced.data_models[]` is referenced by at
least one backend story.
Path: `stories[*]` ↔ upstream `spec-advanced.data_models`
Fail when: a table has no story creating/maintaining/querying it.

### R4 — `role_placeholder`
Check: each story's `role`, `want`, `benefit` is concrete (not "<role>").
Path: `stories[*].{role, want, benefit}`
Fail when: placeholder text or empty.

### R5 — `orphan_group`
Check: every `stories[].group` value matches an existing `groups[].key`.
Path: `stories[*].group` ↔ `groups[*].key`
Fail when: a story references an undefined group key.

### R6 — `non_fibonacci_points`
Check: when `points` is provided, it is in {1, 2, 3, 5, 8, 13}.
Path: `stories[*].points`
Fail when: non-Fibonacci or non-integer value (e.g. 42, 100, "TBD").

### R7 — `dangling_dependency`
Check: every `stories[].depends_on` id matches another `stories[].id`.
Path: `stories[*].depends_on`
Fail when: a dependency id is not declared.

### R8 — `story_missing_owner`
Check: 每個 story 必須有 `owner_role` ∈ {server_engineer | client_engineer | planner | po | art}。
Path: `stories[*].owner_role`
Fail when: 欄位缺失或值不在 enum。

### R9 — `assets_owner_uncovered`
Check: 上游 `assets.assets[*].owner_role` 全集中的每個 role，都至少有一個 story 覆蓋。
Path: `stories[*].owner_role` ↔ upstream `assets.assets[*].owner_role` 全集
Fail when: 某 role 有 N 個 asset 但 stories 沒任何 owner_role=該 role 的條目。

### R10 — `oversized_story`
Check: 1 點 = 1 工作天。每個 owner_role 點數總和 ≤ 公式預估 × 1.3。
**公式**（per-role 工作天）：
- client_engineer = wireframes × 0.5
- server_engineer = apis × 0.4 + tables × 0.2
- art             = unique_asset_subcategories × 0.05
- planner         = 1.0
- po              = 0.5
- total_days      = sum
Path: `stories[*].points` grouped by `owner_role`
Fail when:
- 任一 owner_role 點數 > 公式預估 × 1.3（且超 1 點 slack）→ 切太細或估點高
- 全部 stories 總點數 > total_days × 1.3
- 任一 story points > 5 且描述含「+/與/整合/+ 測試」可分動詞 → 該拆
Fix hint: 由 cross_check.check_scrum_workload + check_timeline_against_formula 程式計算，issue 內含實際數字差。

### R11 — `team_wording_used`
Check: 文案中**不可**出現「團隊」/ 「Team」/ 「組」指代 owner。我們只有一個 scrum team。
Path: stories descriptions / tech_notes / groups.name 等
Fail when: 出現「Server 團隊」「Client 組」「Art Team」等措辭。
Fix hint: 改用「Server 工程師」「Client 工程師」「美術」等個人 role 措辭，或直接用 `owner_role` enum 值。

### R12 — `timeline_scrum_mismatch`
Check: scrum 總點數 ≈ spec-basic.timeline 總週數 × 5（1 週 ≈ 5 工作天）。
       同時兩邊都必須對齊公式預估 total_days（容差 ±30%）。
Path: stories[*].points 總和 ↔ upstream `spec-basic.timeline[*].duration_weeks` 總和
Fail when:
- total_points 與 total_weeks×5 比例偏離 ±30%
- 或任一邊偏離公式預估 total_days 超過 ±30%
Fix hint: 由 cross_check 程式自動算出公式預估，issue 含具體數字；任一邊調整使對齊。

### R `scrum_stories_have_legacy_teams_field`
Check: stories[*] must NOT contain a `teams` field. We use `owner_role`
(enum) only — single multi-role scrum team, no separate departments.
Path: `stories[*].teams`
Fail when: any story includes `teams` key.
Fix hint: 移除 teams 欄位，全部資訊由 owner_role enum 表達。

### R `role_points_exceeds_cap`
Check: 任一 main role (server_engineer/client_engineer/planner/art) 加總
points > 10 → fail.
Path: stories[*].owner_role + points
Fix hint: 拆 stories 或合併估點下降。

### R `role_points_under_estimate`
Check: 任一 main role 加總 < 公式預估 × 50% → 嚴重低估。
Path: stories[*] vs cross_check `_role_budget_days`
Fix hint: 補 stories 或調點。

### R `story_too_large_split_needed`
Check: 任一 story.points > 5 → 違反 INVEST Small。
Path: stories[*].points
Fix hint: 拆 2-3 個子 story（依 subtasks）。

### R `epic_role_missing`
Check: 4 主要 role (server_engineer/client_engineer/planner/art) 各必 1 epic。
Path: epics[*].owner_role
Fix hint: 補缺角色 epic。

### R `story_no_epic_link`
Check: 每 story.epic 必對應 epics[].id。
Fix hint: 補 epic 或修 story.epic 指向。

### R `po_owner_role_used`
Check: 任一 story owner_role = po → PO 不開 work-item story。
Fix hint: 該工作改歸 4 主要 role 之一；PO 工作體現於 epic.po_acceptance。

### R `story_missing_subtasks`
Check: 每 story 必含 subtasks list 子項目（min 1）。
Fix hint: 列出實際 deliverable（1 API / 1 wireframe / 1 asset 等）。

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `module_uncovered`
- `table_no_story`
- `role_placeholder`
- `orphan_group`
- `non_fibonacci_points`
- `dangling_dependency`
- `story_missing_owner`
- `assets_owner_uncovered`
- `oversized_story`
- `team_wording_used`
- `timeline_scrum_mismatch`
- `scrum_stories_have_legacy_teams_field`
- `role_points_exceeds_cap`
- `role_points_under_estimate`
- `story_too_large_split_needed`
- `epic_role_missing`
- `story_no_epic_link`
- `po_owner_role_used`
- `story_missing_subtasks`
