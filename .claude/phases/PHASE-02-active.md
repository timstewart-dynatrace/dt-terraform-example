# Phase 02 -- Combined Auth (Platform Token + API Token) + Dependency Refresh

Status: ACTIVE

## Goal

Bring `dt_client.py` and the `TenantConfig` model into line with current Dynatrace authentication practice — support **both** Platform Tokens (`dt0s16`, `Authorization: Bearer`) and classic Access Tokens (`dt0c01`, `Authorization: Api-Token`), with per-request routing for endpoints that require the classic API Token (the v1.88.0 exclusion list from the Dynatrace Terraform provider). Refresh Python dependencies to current.

Backward-compatible: existing configurations using only `*_TENANT_TOKEN=dt0c01...` continue to work exactly as before.

## Tasks

- [ ] Extend `TenantConfig` with optional `api_token` field; document `token` as polymorphic (Platform Token or classic API Token, auto-detected by prefix)
- [ ] Update `pipelines/core/config.py` to read both `*_TENANT_TOKEN` and a new `*_TENANT_API_TOKEN` from env / pipeline YAML; only one required for back-compat
- [ ] Rewrite `DynatraceClient` request layer:
  - Build `Authorization` header per-request based on URL pattern and token prefix
  - For endpoints in the v1.88.0 classic-only list (synthetic, network monitor, custom device, AG token, API token, credentials, custom tags, host monitoring mode, key requests, hub extension active version, hub extension config, SLO v1/v2), prefer `api_token`; if not set, fall back to a `dt0c01`-prefixed primary `token`
  - For all other endpoints, prefer the primary `token` with prefix-detected header format (`dt0s16` → `Bearer`, `dt0c01` → `Api-Token`)
- [ ] Surface a clear error when an excluded-endpoint request lacks any valid classic-API-Token credential (instead of silent 401)
- [ ] Update `config/.env.example` to document the optional `*_TENANT_API_TOKEN` slot alongside `*_TENANT_TOKEN`
- [ ] Update README "Getting API Tokens" section: Platform Token primary, classic API Token for the excluded-resource subset; cite the v1.88.0 release-note quote as the source
- [ ] Bump `requirements.txt` to current versions (May 2026): requests 2.31.0 → 2.32.5; pyyaml 6.0.1 → 6.0.3; python-dotenv 1.0.0 → 1.2.1; tabulate unchanged at 0.9.0
- [ ] Add `DECISIONS.md` entry: rationale for combined-auth + the v1.88.0 boundary
- [ ] Update `CHANGELOG.md` under `## [Unreleased]`
- [ ] Bump root `CLAUDE.md` Last Updated to current date
- [ ] Smoke-test all Python imports succeed and the basic `verify_connection` flow loads (no live tenant call required in this phase)

## Acceptance Criteria

- Tenant can be configured with: (a) only `*_TENANT_TOKEN` (back-compat — works exactly as today regardless of token prefix); (b) only `*_TENANT_API_TOKEN`; or (c) both
- `DynatraceClient` uses the right Authorization header for every endpoint based on URL + available tokens
- A classic-API-only endpoint request with no classic API Token available produces a clear error message naming the affected endpoint and the env var to set
- Token-format auto-detection by prefix works for both `dt0s16`/`dt0s01` (Bearer) and `dt0c01` (Api-Token)
- All existing Python imports work without changes to call sites that pass a single token (the `token=` keyword still functions)
- `requirements.txt` versions install cleanly via `pip install -r requirements.txt`
- README's auth section reflects the combined-auth landscape with a citation to the v1.88.0 source
- Validator-equivalent: `python3 -c "import pipelines.core.dt_client; import pipelines.core.config; import pipelines.core.types"` returns clean

## Decisions Made This Phase

- 2026-05-11 — Combined-auth model (Platform Token primary + classic API Token for v1.88.0 exclusion list) chosen over Platform-Token-only or classic-only. Rationale: matches the architecture the Dynatrace Terraform provider settled on at v1.88.0; aligns with the AUTOM-07 §3.1 pattern in the Best-Practice-Notebooks-Generator project; lets existing customers keep working with their current single classic-API-Token configuration unchanged.
- 2026-05-11 — Per-request URL-pattern routing (not per-resource explicit declaration) chosen for the auth selector. Rationale: the v1.88.0 exclusion list is endpoint-family-shaped (everything under `/api/synthetic/`, `/api/v1/networkZones`, etc.), so a URL-pattern match keeps the routing logic compact (5-7 patterns) without per-resource if-chains. If the exclusion list grows or the boundary shifts (the Terraform provider has continued to refine it through v1.88-v1.96), one place to update.
