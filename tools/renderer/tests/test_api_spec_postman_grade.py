"""spec-advanced.apis[] must carry Postman/OpenAPI-grade fields.

Old shape (free-text auth string, raw JSON response examples, split
path_params/query_params, no schema) is non-conforming — engineers cannot
write client code without back-and-forth, and the downstream API explorer
can't build a proper Try-It UI without structured auth/parameters/body/
response schemas.

Target shape (per plan):
  auth: { required, type, location?, name?, format?, scopes? }
  parameters: [{ in: path|query|header, name, type, required, description,
                 example?, default?, enum?, pattern?, minimum?, maximum? }]
  request_body: { required, content_type, schema, example }   # POST/PUT/PATCH
  responses: {
    "200": { description, schema, example, headers? },
    "4xx": { description, schema, example }   # at least one error
  }
  rate_limit?, idempotency?, deprecated?, version_added?
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "templates" / "schemas" / "spec-advanced.schema.json"
EXAMPLE_PATH = REPO_ROOT / "templates" / "examples" / "spec-advanced.input.json"
PROMPT_PATH = REPO_ROOT / "templates" / "prompts" / "spec-advanced.prompt.md"
REVIEW_PATH = REPO_ROOT / "templates" / "review" / "spec-advanced.review.md"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def prompt_src() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def review_src() -> str:
    return REVIEW_PATH.read_text(encoding="utf-8")


# ─── A1. Schema declares structured API shape ─────────────────────────────


def test_schema_api_item_required_includes_postman_fields(schema):
    item = schema["properties"]["apis"]["items"]
    required = set(item.get("required", []))
    for f in ("id", "method", "path", "summary", "description", "auth",
              "parameters", "responses"):
        assert f in required, f"apis.items.required missing {f}"


def test_schema_auth_is_structured_object(schema):
    auth = schema["properties"]["apis"]["items"]["properties"]["auth"]
    assert auth.get("type") == "object", "auth must be object (not string)"
    auth_required = set(auth.get("required", []))
    assert "required" in auth_required and "type" in auth_required, (
        "auth must require `required` + `type` fields"
    )
    type_enum = auth["properties"]["type"].get("enum")
    assert type_enum and set(type_enum) >= {"none", "bearer", "api_key", "cookie"}, (
        "auth.type enum must include none/bearer/api_key/cookie"
    )


def test_schema_parameters_is_flat_array_with_in_field(schema):
    params = schema["properties"]["apis"]["items"]["properties"]["parameters"]
    assert params.get("type") == "array"
    item = params["items"]
    required = set(item.get("required", []))
    for f in ("in", "name", "type", "required"):
        assert f in required, f"parameter.required missing {f}"
    in_enum = item["properties"]["in"].get("enum")
    assert in_enum and "body" not in in_enum, "parameter.in must NOT allow 'body'"
    assert set(in_enum) >= {"path", "query", "header"}, "parameter.in needs path/query/header"


def test_schema_request_body_has_schema_not_just_string(schema):
    rb = schema["properties"]["apis"]["items"]["properties"]["request_body"]
    assert rb.get("type") == "object"
    rb_props = rb.get("properties", {})
    for f in ("content_type", "schema", "example"):
        assert f in rb_props, f"request_body.properties missing {f}"


def test_schema_responses_keyed_by_status_with_schema(schema):
    resp = schema["properties"]["apis"]["items"]["properties"]["responses"]
    assert resp.get("type") == "object"
    addl = resp.get("additionalProperties") or resp.get("patternProperties", {})
    if isinstance(addl, dict) and addl.get("properties"):
        item = addl
    else:
        # might use patternProperties
        item = (resp.get("patternProperties") or {}).get("^[1-5][0-9][0-9]$") or addl
    assert item and item.get("properties"), "responses values must have properties"
    for f in ("description", "schema", "example"):
        assert f in item["properties"], f"response item missing {f}"


def test_schema_disallows_legacy_fields(schema):
    """Old string-based fields must be gone."""
    props = schema["properties"]["apis"]["items"].get("properties", {})
    for f in ("path_params", "query_params", "request_body_string", "response_200", "response_errors"):
        # If declared, must not be the legacy string shape
        if f in props:
            assert props[f].get("type") != "string", (
                f"legacy string-shaped {f} still in schema"
            )


# ─── A2. Canonical example uses new shape ─────────────────────────────────


def test_canonical_example_uses_new_shape(example):
    for api in example["apis"]:
        assert isinstance(api.get("auth"), dict), (
            f"{api.get('id')}: auth must be object"
        )
        assert isinstance(api.get("parameters", []), list), (
            f"{api.get('id')}: parameters must be array"
        )
        assert isinstance(api.get("responses"), dict), (
            f"{api.get('id')}: responses must be object"
        )
        assert "summary" in api, f"{api.get('id')}: summary missing"


def test_canonical_example_covers_get_and_post(example):
    """Need at least one GET and one POST/PUT/PATCH so AI sees both shapes."""
    methods = {a["method"].upper() for a in example["apis"]}
    assert "GET" in methods, "canonical example missing GET endpoint"
    assert methods & {"POST", "PUT", "PATCH"}, "canonical example missing write endpoint"


def test_canonical_example_post_has_request_body(example):
    write_apis = [a for a in example["apis"] if a["method"].upper() in ("POST", "PUT", "PATCH")]
    assert write_apis, "no write API in example"
    for a in write_apis:
        rb = a.get("request_body")
        assert rb, f"{a['id']}: write method must have request_body"
        assert "schema" in rb, f"{a['id']}: request_body.schema missing"


def test_canonical_example_has_success_and_error(example):
    """Each endpoint needs a 2xx success and at least one 4xx error
    (POST create uses 201; others typically 200)."""
    for a in example["apis"]:
        codes = set(a.get("responses", {}).keys())
        assert any(c.startswith("2") for c in codes), (
            f"{a['id']}: missing any 2xx success response"
        )
        assert any(c.startswith("4") for c in codes), (
            f"{a['id']}: missing any 4xx error response"
        )


def test_canonical_example_validates_against_schema(example, schema):
    from jsonschema import Draft7Validator
    errs = list(Draft7Validator(schema).iter_errors(example))
    if errs:
        msgs = "\n".join(f"  - {'.'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errs[:8])
        pytest.fail(f"canonical example fails schema validation:\n{msgs}")


# ─── A3. Prompt teaches new shape ─────────────────────────────────────────


def test_prompt_documents_structured_auth(prompt_src):
    assert "auth.type" in prompt_src or "auth: {" in prompt_src or '"auth":' in prompt_src, (
        "prompt must show auth as structured object"
    )
    assert "bearer" in prompt_src.lower() and "api_key" in prompt_src.lower(), (
        "prompt must list auth type enum"
    )


def test_prompt_documents_parameters_with_in(prompt_src):
    assert "parameters" in prompt_src
    assert '"in"' in prompt_src or 'in: ' in prompt_src or '`in`' in prompt_src, (
        "prompt must document parameter.in field"
    )


def test_prompt_documents_request_body_schema(prompt_src):
    assert "request_body" in prompt_src
    assert "schema" in prompt_src, "prompt must mention body schema (not just example)"


def test_prompt_documents_responses_with_schema_and_errors(prompt_src):
    assert "responses" in prompt_src
    assert "4xx" in prompt_src or "401" in prompt_src or "400" in prompt_src, (
        "prompt must require at least one error response"
    )


def test_prompt_forbids_legacy_fields(prompt_src):
    # Prompt should NOT instruct AI to write the old fields
    assert "path_params" not in prompt_src, "prompt still mentions legacy path_params"
    assert "query_params" not in prompt_src, "prompt still mentions legacy query_params"
    assert "response_200" not in prompt_src, "prompt still mentions legacy response_200"
    assert "response_errors" not in prompt_src, "prompt still mentions legacy response_errors"


# ─── B. Template renders new structured shape ─────────────────────────────


@pytest.fixture(scope="module")
def rendered_spec_advanced(example):
    """Render spec-advanced.md from canonical example."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))
    import render
    return render.render("spec-advanced", example)


def test_render_has_authentication_section(rendered_spec_advanced):
    md = rendered_spec_advanced
    assert "Authentication" in md or "認證" in md
    # Structured auth fields surfaced
    assert "bearer" in md.lower() or "Bearer" in md
    assert "Authorization" in md, "auth.name (Authorization) must be rendered"


def test_render_has_parameters_table_with_in_column(rendered_spec_advanced):
    """Parameters table must have an `in` column (path/query/header)."""
    md = rendered_spec_advanced
    assert "Parameters" in md or "參數" in md
    # the canonical example has path + query + header params; all three should appear
    assert "path" in md and "query" in md and "header" in md, (
        "parameters table must surface in=path/query/header"
    )


def test_render_has_request_body_with_schema_table(rendered_spec_advanced):
    """POST/PATCH endpoints must render request_body with schema (not just example)."""
    md = rendered_spec_advanced
    assert "Request Body" in md or "請求內文" in md
    assert "application/json" in md, "request_body.content_type must be rendered"
    # canonical POST example has fields name/kind/owner_id — at least name + kind shown
    assert "name" in md and "kind" in md


def test_render_has_responses_per_status_code(rendered_spec_advanced):
    """Responses section must have a subsection per status code with schema + example."""
    md = rendered_spec_advanced
    # canonical example covers 200/201/400/401/404 across 3 endpoints
    assert "200" in md and "201" in md and "401" in md
    # Each response example body should be present (JSON code block)
    assert "unauthorized" in md, "401 response example body not rendered"
    assert "resource not found" in md.lower() or "resource_not_found" in md.lower(), (
        "404 response example body not rendered"
    )


def test_render_has_rate_limit_when_present(rendered_spec_advanced):
    md = rendered_spec_advanced
    # canonical example has rate_limit on two endpoints
    assert "rate" in md.lower() or "速率" in md or "Rate Limit" in md
    assert "per_minute" in md or "per minute" in md.lower() or "/分鐘" in md or "/min" in md


def test_review_md_has_postman_grade_rules(review_src):
    """spec-advanced.review.md must include the 7 new API quality rules."""
    expected_tags = [
        "api_auth_not_object",         # auth must be object not string
        "api_auth_required_no_type",   # auth.required=true + type=none
        "api_params_contains_body",    # parameter.in must not be 'body'
        "api_write_no_request_body",   # POST/PUT/PATCH missing request_body
        "api_responses_no_success_or_error",  # responses must have 2xx + 4xx
        "api_response_no_schema",      # response only has example
        "api_rate_limit_missing",      # perf mentions QPS but no rate_limit
    ]
    for tag in expected_tags:
        assert tag in review_src, f"review.md missing rule tag `{tag}`"


def test_review_md_whitelist_includes_new_tags(review_src):
    """The ISSUE CATEGORY TAGS whitelist must list every new tag."""
    # naive: every tag should appear at least twice (rule definition + whitelist)
    expected_tags = [
        "api_auth_not_object",
        "api_auth_required_no_type",
        "api_params_contains_body",
        "api_write_no_request_body",
        "api_responses_no_success_or_error",
        "api_response_no_schema",
        "api_rate_limit_missing",
    ]
    for tag in expected_tags:
        assert review_src.count(tag) >= 2, (
            f"tag `{tag}` should appear in both rule def AND whitelist"
        )


# ─── E. docs.html.tmpl API explorer UI (4-tab + live preview + mock + auth) ──


@pytest.fixture(scope="module")
def docs_template_src() -> str:
    return (REPO_ROOT / "templates" / "docs.html.tmpl").read_text(encoding="utf-8")


def test_renderapi_has_tab_structure(docs_template_src):
    """renderApi must build a Postman-style 4-tab UI (Params/Auth/Headers/Body)."""
    src = docs_template_src
    assert "tab-params" in src and "tab-auth" in src and "tab-headers" in src and "tab-body" in src, (
        "renderApi must declare tab markers: tab-params / tab-auth / tab-headers / tab-body"
    )


def test_renderapi_handles_request_body_schema(docs_template_src):
    """Body tab must render request_body.schema fields (not just raw JSON)."""
    src = docs_template_src
    assert "request_body" in src, "renderApi must read request_body"
    assert "schema" in src and "properties" in src, (
        "renderApi must walk request_body.schema.properties"
    )


def test_renderapi_renders_auth_input_when_required(docs_template_src):
    """Auth tab must render an input when ep.auth.required is true,
    and must reference auth.type / auth.required so mock + cURL can use it."""
    src = docs_template_src
    assert "auth.required" in src, (
        "renderApi/mock must branch on auth.required"
    )
    assert "auth.type" in src or "auth.format" in src or "auth.name" in src, (
        "renderApi must surface auth structured fields (type/format/name)"
    )


def test_live_preview_updates_on_input(docs_template_src):
    """Inputs must trigger preview recompute (no need to click anything)."""
    src = docs_template_src
    # Some `addEventListener('input', ...)` or `oninput=` must be present
    # within renderApi's scope or wired after render.
    assert "'input'" in src or 'oninput' in src or '"input"' in src, (
        "renderApi must listen to input events for live preview"
    )
    # And a refresh/preview function name
    assert "refreshPreview" in src or "updatePreview" in src or "renderPreview" in src, (
        "renderApi must call a preview refresh function on input"
    )


def test_mock_returns_401_when_auth_required_and_empty(docs_template_src):
    """tryApi must return 401 when endpoint requires auth and token input is empty."""
    src = docs_template_src
    assert "401" in src, "tryApi must reference 401"
    # branch on auth required + empty token
    assert "auth.required" in src or "ep.auth" in src, (
        "tryApi must check auth.required before deciding response"
    )


def test_mock_response_echoes_request_as_debug(docs_template_src):
    """Mock response body must include a _debug block echoing the request
    (URL/headers/body) so the user sees their inputs were received."""
    src = docs_template_src
    assert "_debug" in src, "mock response must echo request as _debug"


def test_copy_curl_reads_live_preview(docs_template_src):
    """copyCurl should copy from the live preview element, not recompute
    silently (so what user sees == what gets copied)."""
    src = docs_template_src
    # Either reads from preview element, or refreshes preview right before copy.
    # Heuristic: presence of `clipboard.writeText` plus reference to preview/cURL element.
    assert "clipboard" in src, "copyCurl missing clipboard API"


def test_docs_api_explorer_data_carries_full_structure():
    """docs canonical example api_explorer entries must carry the same
    structured fields as spec-advanced (auth as object, parameters as flat
    array, responses keyed by status with schema+example)."""
    docs_ex = json.loads((REPO_ROOT / "templates" / "examples" / "docs.input.json").read_text(encoding="utf-8"))
    for ae in docs_ex.get("api_explorer", []):
        assert isinstance(ae.get("auth"), dict), f"{ae.get('id')}: auth must be object"
        assert isinstance(ae.get("parameters"), list), f"{ae.get('id')}: parameters must be array"
        assert isinstance(ae.get("responses"), dict), f"{ae.get('id')}: responses must be object"
        for code, resp in ae["responses"].items():
            assert "schema" in resp and "example" in resp, (
                f"{ae.get('id')}.responses[{code}] needs schema + example"
            )


# ─── D. cross_check programmatic validation ───────────────────────────────


def test_cross_check_canonical_example_passes():
    """Canonical example (newly-shaped) must have zero issues from the
    Postman-grade checker."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))
    from cross_check import check_apis_postman_grade
    ex = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    issues = check_apis_postman_grade(ex)
    assert not issues, f"canonical example should pass; got {[(i.category, i.detail) for i in issues]}"


def test_cross_check_flags_string_auth():
    import sys
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))
    from cross_check import check_apis_postman_grade
    data = {"apis": [{"id": "x", "method": "GET", "path": "/x", "summary": "x",
                      "description": "x", "auth": "Bearer Token",
                      "parameters": [], "responses": {
                          "200": {"description": "ok", "schema": {"type": "object"}, "example": {}},
                          "401": {"description": "no", "schema": {"type": "object"}, "example": {}}}}]}
    issues = check_apis_postman_grade(data)
    cats = {i.category for i in issues}
    assert "api_auth_not_object" in cats


def test_cross_check_flags_in_body_in_parameters():
    import sys
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))
    from cross_check import check_apis_postman_grade
    data = {"apis": [{"id": "x", "method": "POST", "path": "/x", "summary": "x",
                      "description": "x",
                      "auth": {"required": False, "type": "none"},
                      "parameters": [{"in": "body", "name": "foo", "type": "string", "required": True}],
                      "request_body": {"required": True, "content_type": "application/json",
                                        "schema": {"type": "object"}, "example": {}},
                      "responses": {
                          "201": {"description": "ok", "schema": {"type": "object"}, "example": {}},
                          "400": {"description": "no", "schema": {"type": "object"}, "example": {}}}}]}
    issues = check_apis_postman_grade(data)
    assert "api_params_contains_body" in {i.category for i in issues}


def test_cross_check_flags_post_without_request_body():
    import sys
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))
    from cross_check import check_apis_postman_grade
    data = {"apis": [{"id": "x", "method": "POST", "path": "/x", "summary": "x",
                      "description": "x",
                      "auth": {"required": False, "type": "none"},
                      "parameters": [],
                      "responses": {
                          "201": {"description": "ok", "schema": {"type": "object"}, "example": {}},
                          "400": {"description": "no", "schema": {"type": "object"}, "example": {}}}}]}
    issues = check_apis_postman_grade(data)
    assert "api_write_no_request_body" in {i.category for i in issues}


def test_cross_check_flags_response_without_error():
    import sys
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))
    from cross_check import check_apis_postman_grade
    data = {"apis": [{"id": "x", "method": "GET", "path": "/x", "summary": "x",
                      "description": "x",
                      "auth": {"required": False, "type": "none"},
                      "parameters": [],
                      "responses": {
                          "200": {"description": "ok", "schema": {"type": "object"}, "example": {}}}}]}
    issues = check_apis_postman_grade(data)
    assert "api_responses_no_success_or_error" in {i.category for i in issues}


def test_cross_check_flags_response_without_schema():
    import sys
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))
    from cross_check import check_apis_postman_grade
    data = {"apis": [{"id": "x", "method": "GET", "path": "/x", "summary": "x",
                      "description": "x",
                      "auth": {"required": False, "type": "none"},
                      "parameters": [],
                      "responses": {
                          "200": {"description": "ok", "example": {}},
                          "401": {"description": "no", "schema": {"type": "object"}, "example": {}}}}]}
    issues = check_apis_postman_grade(data)
    assert "api_response_no_schema" in {i.category for i in issues}


def test_cross_check_flags_rate_limit_missing_when_perf_mentions_qps():
    import sys
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))
    from cross_check import check_apis_postman_grade
    data = {"apis": [{"id": "x", "method": "GET", "path": "/x", "summary": "x",
                      "description": "x",
                      "auth": {"required": False, "type": "none"},
                      "parameters": [],
                      "perf": "p95 < 50ms, QPS 500",
                      "responses": {
                          "200": {"description": "ok", "schema": {"type": "object"}, "example": {}},
                          "401": {"description": "no", "schema": {"type": "object"}, "example": {}}}}]}
    issues = check_apis_postman_grade(data)
    assert "api_rate_limit_missing" in {i.category for i in issues}


def test_render_does_not_use_legacy_fields(rendered_spec_advanced, example):
    """Template must not silently fall back to legacy field names."""
    md = rendered_spec_advanced
    # canonical example no longer has these — if md contains them, template
    # is reading wrong field
    assert "response_200" not in md
    assert "response_errors" not in md
