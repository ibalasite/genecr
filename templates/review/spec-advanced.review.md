# spec-advanced review rules

You are reviewing `spec-advanced.input.json`. This is the technical
elaboration of spec-basic. Architecture, APIs, DB schema, Redis schema —
all must be coherent with spec-basic and self-consistent.

## Required checks

1. **architecture.diagram**: non-empty valid Mermaid syntax. Reject empty
   string, placeholder text, or non-Mermaid prose.

2. **APIs vs upstream**: every endpoint in `apis[]` either implements a
   `user_journey` step from spec-basic, or supports a wireframe interaction.
   Flag APIs with no upstream purpose.

3. **DB schema completeness**: each `data_models[].kind = mysql|postgres`
   entry has:
   - non-empty `fields[]` with name/type per row
   - non-empty `indexes` listing PK + secondary indexes
   - `create_table_sql` matching the field/index declarations
   Flag mismatches between fields and CREATE TABLE.

4. **SQL covers indexes**: every `db_queries[].sql` WHERE/JOIN column appears
   in some `data_models[].indexes`. (The program cross_check enforces this
   mechanically; you cross-verify the SQL actually answers the scenario.)

5. **Redis schema**: each `data_models[].kind = redis` has a `redis_pattern`,
   `value_type` ∈ {string, hash, list, zset, set}, and a TTL declaration.
   `redis_ops` commands match the declared value_type (no LPUSH on a hash).

6. **state machine**: `client.states[]` from/trigger/to all reference
   declared states. No orphan states. Initial state present.

7. **business_logic**: each entry's `pseudocode` references real APIs +
   real data_models. No magic.

8. **template noise**: reject any `<...>` / "TBD" placeholders.

## Issue category tags

- `mermaid_invalid`, `api_no_upstream`, `schema_field_index_mismatch`,
  `sql_doesnt_answer_scenario`, `redis_command_type_mismatch`,
  `orphan_state`, `pseudocode_magic`, `template_noise`
