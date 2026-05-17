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
Check: 1 點 = 1 工作天。預設 1-3 點；>80% 的 stories 應 ≤ 3 點。8/13 點僅用於真 epic（描述明顯不可拆才允許）。
       單一 feature stories 總點數 ≤ feature 規模上限（小活動 15、中型 60、大型 80）。
Path: `stories[*].points`
Fail when:
- 任一 story points > 5 且描述含「+」「與」「整合」「+ 測試」等可分動詞 → 該拆
- 全部 stories 總點數超過該 feature timeline_total_weeks × 7（容差 1.4x）
Fix hint: 拆成更小條目；單 API 1-2 點不該 8 點。

### R11 — `team_wording_used`
Check: 文案中**不可**出現「團隊」/ 「Team」/ 「組」指代 owner。我們只有一個 scrum team。
Path: stories descriptions / tech_notes / groups.name 等
Fail when: 出現「Server 團隊」「Client 組」「Art Team」等措辭。
Fix hint: 改用「Server 工程師」「Client 工程師」「美術」等個人 role 措辭，或直接用 `owner_role` enum 值。

### R12 — `timeline_scrum_mismatch`
Check: scrum 總點數 ≈ spec-basic.timeline 總週數 × 5（容差 ±50%；1 週 ≈ 5 工作天）。
Path: stories[*].points 總和 ↔ upstream `spec-basic.timeline[*].duration_weeks` 總和
Fail when: 兩邊差超過 1.5x（如 spec 寫 2 週 = 期望 10 點，scrum 寫 30 點，或 spec 寫 7 週 = 期望 35 點，scrum 寫 10 點）。
Fix hint: 任一邊調整，使兩邊規模匹配（小活動 timeline ≤ 2 週 + scrum 8-12 點為標準）。

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
