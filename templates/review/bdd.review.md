# bdd review rules

You are reviewing `bdd.input.json`. Each scenario must rigorously test
spec-basic acceptance criteria and spec-advanced API behaviors. Sequence
diagrams are MANDATORY and must accurately depict the scenario.

## Required checks

1. **sequence_diagram presence**: every `scenarios[]` has a non-empty
   `sequence_diagram` containing valid Mermaid `sequenceDiagram` syntax.
   Reject empty strings or non-Mermaid prose. **This is user-flagged
   critical**; flag every missing/broken case.

2. **sequence_diagram coverage**: the participants in the diagram include
   the actors referenced in `gherkin_zh` Given/When/Then steps. A scenario
   "玩家點擊登入 → 後端驗證 → 回應" must show Player + Backend in the
   diagram.

3. **Gherkin structure**: each `gherkin_zh` has Given / When / Then
   (中文 假設/當/那麼 acceptable). Reject scenarios with only a When step.

4. **English mirror**: if `gherkin_en` is present, its structure mirrors
   `gherkin_zh`. Flag divergence in step count or order.

5. **API coverage**: every API in `scenarios[].apis` is also declared in
   `spec-advanced.apis`. Flag references to undeclared APIs.

6. **acceptance coverage**: across all scenarios, each
   `spec-basic.acceptance_criteria` is touched by at least one scenario's
   `Then` step. Flag uncovered criteria.

7. **negative paths**: at least 30% of scenarios test failure / edge cases,
   not just happy path.

8. **template noise**: reject `<...>` placeholders.

## Issue category tags

- `sequence_diagram_missing`, `sequence_diagram_invalid_mermaid`,
  `participants_not_in_gherkin`, `gherkin_incomplete`, `mirror_divergent`,
  `api_undeclared`, `acceptance_uncovered`, `no_negative_scenarios`,
  `template_noise`
