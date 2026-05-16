# spec-advanced review rules

You review `spec-advanced.input.json`. Apply each numbered rule. Cite the
real input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder string.
Fail when: any string field equals or contains `<...>` / "TBD" / "<待補>".

### R2 — `mermaid_invalid`
Check: `architecture.diagram` is a non-empty Mermaid source.
Path: `architecture.diagram`
Fail when: empty string, prose paragraph, or text that doesn't start with
a Mermaid keyword (graph / flowchart / sequenceDiagram / erDiagram /
classDiagram / stateDiagram).

### R3 — `api_no_upstream`
Check: every endpoint in `apis[]` serves a `spec-basic.user_journey` step
or a wireframe interaction.
Path: `apis[*]`
Fail when: an endpoint has no traceable upstream purpose.

### R4 — `schema_field_index_mismatch`
Check: each `data_models[]` entry with kind ∈ {mysql, postgres, sqlite}
has fields[] and indexes; `create_table_sql` declares the same field
names and the same index names.
Path: `data_models[*].{fields, indexes, create_table_sql}`
Fail when: a field in `fields[]` is absent from `create_table_sql`, or
an index named in `indexes` is absent from `create_table_sql`.

### R5 — `sql_no_matching_index`
Check: each entry in `db_queries[]` has a WHERE/JOIN column covered by
some declared index in `data_models[*].indexes`.
Path: `db_queries[*].sql` ↔ `data_models[*].indexes`
Fail when: a WHERE/JOIN column has no covering index.

### R6 — `redis_command_type_mismatch`
Check: commands in `redis_ops[]` match the `value_type` declared in the
corresponding `data_models[kind=redis].value_type`.
Path: `redis_ops[*].commands` ↔ `data_models[*].value_type`
Fail when: e.g. LPUSH used on a key declared as hash, HSET used on string.

### R7 — `orphan_state`
Check: every `client.states[].from` and `client.states[].to` references
a state mentioned by some other transition (no orphans).
Path: `client.states[*]`
Fail when: a state name appears only once across all transitions.

### R8 — `pseudocode_magic`
Check: each `business_logic[].pseudocode` references real APIs from
`apis[]` and real tables from `data_models[]`.
Path: `business_logic[*].pseudocode`
Fail when: pseudocode invokes API names or table names that don't exist.

### R9 — `count_inconsistent`
Check: `counts.api_endpoints` (if present) equals `len(apis)`;
`counts.tables` equals number of relational data_models;
`counts.redis_keys` equals number of redis data_models.
Path: `counts.*` ↔ `apis` / `data_models`
Fail when: declared count differs from actual.

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `mermaid_invalid`
- `api_no_upstream`
- `schema_field_index_mismatch`
- `sql_no_matching_index`
- `redis_command_type_mismatch`
- `orphan_state`
- `pseudocode_magic`
- `count_inconsistent`
