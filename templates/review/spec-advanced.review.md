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

### R10 — `api_auth_not_object`
Check: every `apis[].auth` is a structured object (not a free-text string).
Path: `apis[*].auth`
Fail when: `auth` is a string like `"Bearer Token"` instead of `{required, type, ...}`.
Fix hint: convert to `{"required": true, "type": "bearer", "location": "header", "name": "Authorization", "format": "Bearer {token}"}`.

### R11 — `api_auth_required_no_type`
Check: when `apis[].auth.required` is true, `apis[].auth.type` MUST be one of
`bearer` / `api_key` / `cookie` / `basic` (not `none`).
Path: `apis[*].auth.{required, type}`
Fail when: `required=true` but `type=none` or `type` missing.

### R12 — `api_params_contains_body`
Check: no entry in `apis[].parameters[]` has `in == "body"`. Body fields belong
in `apis[].request_body.schema.properties`, not parameters.
Path: `apis[*].parameters[*].in`
Fail when: any parameter has `"in": "body"`.

### R13 — `api_write_no_request_body`
Check: every endpoint with `method` in {POST, PUT, PATCH} has `apis[].request_body`
with `schema` (not just example).
Path: `apis[*].{method, request_body.schema}`
Fail when: a write endpoint lacks `request_body` or `request_body.schema`.

### R14 — `api_responses_no_success_or_error`
Check: every `apis[].responses` contains at least one 2xx (success) status code
AND at least one 4xx (client error) status code.
Path: `apis[*].responses`
Fail when: only 200 listed (no error), or only errors listed (no success).
Fix hint: minimum {200 OR 201, 400 OR 401 OR 404}.

### R15 — `api_response_no_schema`
Check: every response entry under `apis[].responses[code]` has a `schema` field
(not only `example`). Engineers need to know fields/types/required-ness without
reverse-engineering the example payload.
Path: `apis[*].responses[*].schema`
Fail when: a response entry has `example` but no `schema`.

### R16 — `api_rate_limit_missing`
Check: when `apis[].perf` mentions a throughput number (regex matches `QPS\s*\d+`
or `req/s` or `/min`), the endpoint also declares structured `rate_limit`.
Path: `apis[*].{perf, rate_limit}`
Fail when: `perf` references QPS but `rate_limit` is absent.
Fix hint: `"rate_limit": {"per_minute": <n>, "per_user": true|false}`.

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
- `api_auth_not_object`
- `api_auth_required_no_type`
- `api_params_contains_body`
- `api_write_no_request_body`
- `api_responses_no_success_or_error`
- `api_response_no_schema`
- `api_rate_limit_missing`
