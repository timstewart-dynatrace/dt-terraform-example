# Decisions

This file tracks all non-trivial technical decisions made during this project.

Use the format below. Log decisions **at the time** they're made, not retroactively.

---

## 2026-04-16 — Dual Python/Shell Script Approach

**Chosen:** Provide both Python and Shell implementations for migration scripts
**Alternatives:** Python-only, Shell-only, Go CLI
**Why:** Maximizes accessibility across environments. Some production servers only have Bash; some teams prefer Python for its readability and error handling. Both scripts share the same workflow and produce identical results.
**Trade-offs:** Two codepaths to maintain. Changes must be reflected in both implementations.
**Revisit if:** One implementation becomes significantly more popular, or maintenance burden grows.

---

## 2026-04-16 — Terraform-Compatible Workflow (Not Direct Terraform Provider)

**Chosen:** Python/Shell scripts that orchestrate Terraform-compatible config export and deployment via Dynatrace APIs
**Alternatives:** Pure Terraform HCL with `dynatrace-oss/dynatrace` provider, Monaco CLI
**Why:** Provides a migration-focused workflow (backup, validate, deploy) that Terraform alone does not offer out of the box. Terraform provider is the underlying model but the scripts add safety layers (dry-run, backup-first, selective type migration).
**Trade-offs:** Not pure infrastructure-as-code. Users don't get Terraform state management or plan/apply workflow directly.
**Revisit if:** Project scope shifts toward ongoing config management rather than one-time migration.

---

## 2026-04-16 — Backup-First Deployment Behavior

**Chosen:** Back up target tenant configuration by default before deploying changes
**Alternatives:** Skip backup for speed, no backup option at all
**Why:** Safety default. Configuration migration is destructive — overwriting target config without backup risks data loss. The backup-first approach makes rollback possible.
**Trade-offs:** Slower migration due to additional API calls. Disk space for backup storage. Shell script provides `--no-backup` flag for cases where speed matters. Python script skips backup in dry-run mode (no changes applied, so no backup needed).
**Revisit if:** Backup adds unacceptable latency for large tenants, or if a separate backup tool is adopted.

---

## 2026-05-11 — Reference Currency Directive Adopted from Best-Practice-Notebooks-Generator

**Chosen:** Adopt the Reference Currency directive pattern from the Best-Practice-Notebooks-Generator project (`workflow.md` § Reference Currency in that project), adapted to this smaller codebase. Two directives: next-touch reference standardization + deep content verification via `scripts/validate_citation_urls.py`.

**Alternatives:**
- Do nothing — accept that cited URLs will silently rot until someone notices a 404.
- Just write a URL-liveness check script without a documented rule — half-measure; you have the tool but not the discipline to actually use it on PR review.
- Copy the Notebooks-Generator's full workflow.md verbatim — overkill for a single-Python-codebase project; that document is sized for 446 notebooks across 34 series.

**Why:** The single most load-bearing citation in this project — the v1.88.0 release-note quote that defines the auth-routing boundary in `dt_client.py` — is the kind of statement that Dynatrace can shift in any future provider release. Without a documented discipline, the boundary list goes stale silently, and our routing produces 401s or silent breakage. The directive makes the maintenance routine rather than ad-hoc. Other Dynatrace-cited URLs (Platform Tokens docs, classic Access Tokens docs, provider releases) have the same drift risk on a slower cadence.

**Trade-offs:** A monthly URL liveness check is a small recurring cost. Manual content-drift spot-checks require human judgment — not automated. The rule is opinionated about format (`[Title (publisher)](URL)` minimal) which someone might find restrictive.

**Revisit if:** This project's citation surface grows substantially (more docs / more code / more vendor surfaces beyond Dynatrace) — the script's scan scope or the directive's cadence might need to scale. Or if Dynatrace publishes a stable reference for the auth-routing boundary that removes the need to track release notes.

---

## 2026-05-11 — pytest + `responses` for the Test Suite

**Chosen:** Use pytest (with parametrize) for unit tests and the `responses` library for HTTP-level mocking. Tests live in `tests/`; configuration in `pyproject.toml`; pytest invoked via `python -m pytest`. CI runs on Python 3.9, 3.11, 3.12.

**Alternatives:**
- `unittest` from the standard library — no extra deps, but verbose for parametrized cases and lacks pytest's fixture model.
- `unittest.mock` directly on `requests.Session` — works but produces less-clear failure messages than `responses`; `responses` registers expected URL + method and fails with "no match for `<request>`" rather than a stack trace deep in `requests`.

**Why:** The auth-routing logic in `dt_client.py` benefits from `pytest.mark.parametrize` — one decorator generates ~25 separate test cases for the URL-pattern matching, much cleaner than equivalent unittest. `responses` is the standard choice for testing `requests`-based clients and gives readable failures when a test sends the wrong header. Three Python versions in CI catches forward-compat issues without going to bleeding-edge.

**Trade-offs:** Two extra dev dependencies. Python 3.9 in CI keeps us pinned to features available there (no PEP 695 generics, no match statements in production code — these would break the 3.9 leg).

**Revisit if:** Python 3.9 reaches EOL and we want to bump the floor; or if the test suite grows past the point where `responses` starts feeling heavyweight (consider `pytest-httpx` if we ever switch HTTP libraries).

---

## 2026-05-11 — Combined Auth (Platform Token + classic API Token, URL-routed)

**Chosen:** Support both Platform Tokens (`dt0s16` / `dt0s01`, sent as `Authorization: Bearer`) and classic Access Tokens (`dt0c01`, sent as `Authorization: Api-Token`) in a single client. Auto-detect the header format by token prefix. Add an optional secondary `*_TENANT_API_TOKEN` slot used only for endpoints in the v1.88.0 Dynatrace-Terraform-provider exclusion list (synthetic monitors, network monitors, AG/API tokens, credentials, custom devices, custom tags, host monitoring mode, key requests, hub extension active version + config, SLO v1/v2).

**Alternatives:**
- Platform-Token-only — fails on the v1.88.0 exclusion list.
- Classic-API-Token-only — works (status quo before Phase 02) but doesn't align with Dynatrace's current default for new tenants and loses the new-token-prefix scope coverage that Platform Tokens give.
- Two completely separate clients (one Platform, one classic) — doubles the code and call-sites have to choose; routing by URL inside a single client is cleaner.

**Why:** Matches the architecture the Dynatrace Terraform provider settled on at v1.88.0 — *"The OAuth functionality has been removed for the following resources, which previously relied on the `environment-api:*` scopes"* (release notes). The provider implements per-resource auth routing because the underlying REST API has the same boundary. We mirror that. Aligns with the combined-auth pattern in the Best-Practice-Notebooks-Generator project's AUTOM-07 §3.1.

**Trade-offs:** Two tokens to manage per tenant (when the primary is a Platform Token). The URL-pattern routing list (`_CLASSIC_API_TOKEN_URL_PATTERNS` in `dt_client.py`) is a maintenance surface — if Dynatrace shifts the boundary again, that list needs updating. Backward compatibility preserved: a config with only `*_TENANT_TOKEN=dt0c01...` works identically to before (the primary token is classic-shaped, so the excluded endpoints reuse it via the fall-back path).

**Revisit if:** Dynatrace publishes a clean source-of-truth list of which endpoints accept which token type (today the v1.88.0 release notes are the most concrete source). Or if the boundary shifts substantially across a future provider major version.

---

## 2026-05-18 — Two auth models coexist (tenant tokens for migration, OAuth client for IAM)

**Chosen:** Add `terraform/iam/` scaffold using account-level OAuth client auth (`DT_CLIENT_ID` + `DT_CLIENT_SECRET` + `DT_ACCOUNT_ID`) targeting the account API (`api.dynatrace.com`), while keeping the existing tenant-token auth (Platform Token / classic API Token) for the migration pipelines targeting `<tenant>.live.dynatrace.com`. Two completely separate auth models in one repo; the IAM scaffold owns its own README and credential docs, separate from `config/.env.example`.

**Alternatives:**
- Unify under one client (extend `pipelines/core/dt_client.py`) — wrong direction. IAM and migration target different APIs, use different credential models, and have different lifecycles. Forcing them into one client would be a leaky abstraction with conditional routing for two different audiences.
- Put IAM in a separate repo — clean separation but loses the value of "all Dynatrace tooling discoverable in one place." User explicitly chose the subdirectory approach.
- Use Platform Tokens for IAM — not supported by the provider. The [dynatrace_iam_group resource (Dynatrace provider docs)](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest/docs/resources/iam_group) explicitly requires *"the environment variables `DT_CLIENT_ID`, `DT_CLIENT_SECRET`, `DT_ACCOUNT_ID` with an OAuth client"*. There is no Platform-Token path.

**Why:** IAM is account-level (one account → many environments); migration is tenant-level (per-environment config). The `dynatrace-oss/dynatrace` provider mandates OAuth client credentials for IAM resources with scopes (`account-idm-read/write`, `iam-policies-management`, `account-env-read`) that don't exist on Platform Tokens. The split is enforced by the provider, not by us — fighting it would be wasted work.

**Trade-offs:** Two sets of credentials to manage. README structure now has two distinct credential setup paths (tenant tokens in the root `README.md` "Getting API Tokens" section; OAuth client in `terraform/iam/README.md`). New contributors must understand which subtree uses which auth model. Acceptable cost — the alternative (one client doing both) would be worse for understandability.

**Revisit if:** Dynatrace consolidates auth across the account and tenant APIs (no roadmap signal as of provider v1.96.0). Or if the IAM Terraform surface grows large enough to justify its own repo (currently 8 small `.tf` files plus a README — well within "one subdirectory" scale).

---

## 2026-05-18 — IAM permission DSL discovered via existing-policies dump (no public catalog)

**Chosen:** Use the account's own existing policies as the authoritative reference for the Dynatrace IAM permission DSL (`service:resource:action` tokens). Built `scripts/iam-list.sh` to automate dumping groups + policies + boundaries via the Account Management API and emit a deduplicated permission-token list. Operators are instructed to run this *before* writing new `statement_query` content.

**Alternatives:**
- Trust the `dynatrace-oss/dynatrace` provider's docs — the registry pages and `docs/resources/iam_policy.md` only show one canonical example (`ALLOW settings:objects:read, settings:schemas:read WHERE settings:schemaId = "string";`). The provider's integration tests use even less. Not enough to cover a real policy authoring need.
- Trust Dynatrace's official IAM permission catalog at `docs.dynatrace.com` — multiple WebFetch attempts at the landing page returned navigation hubs that *referenced* a catalog page but didn't contain the actual list. No public URL we could find lists every valid token.
- Use AWS-IAM-style assumption (`:read`/`:write`/`:delete` exist for every resource) — burned us. `settings:objects:delete` extrapolated this way; HTTP 400 at apply. Tokens are NOT regular.

**Why:** Multiple failed `terraform apply` attempts (HTTP 400 with the provider stripping the body) proved that token names are not derivable from patterns. The single source of truth that always exists is the account itself — every existing policy uses real tokens that Dynatrace accepted. Dumping 133 policies from one account produced a deduplicated list of ~130 unique tokens — that's the operational vocabulary for that account. The discovery script makes this routine rather than ad-hoc curl-and-grep.

**Trade-offs:** Per-account discovery rather than a vendor-published reference. A brand-new account with no policies has no vocabulary to copy from — operators on greenfield accounts have to write a first policy speculatively, see what the API accepts, and iterate. The script doesn't help with that bootstrap problem. Also the dump is point-in-time; if Dynatrace ships new permission tokens in a future release, an operator wouldn't see them until they appear in someone's policy.

**Revisit if:** Dynatrace publishes a stable IAM permission catalog URL we can WebFetch reliably (would let us replace the dump with a doc lookup). Or if the dynatrace-oss provider adds a `terraform-provider-dynatrace -list-iam-permissions`-style flag that prints the catalog from its embedded schema.

---

## 2026-05-18 — `settings:objects:admin` replaces non-existent `:delete` verb

**Chosen:** For `settings:objects`, use only the verbs `:read`, `:write`, and `:admin`. Use `:admin` as the umbrella verb when a policy needs full management (which would conceptually include delete). Do NOT use `:delete` for `settings:objects` — it is not a valid token.

**Alternatives:**
- List `:read`, `:write`, `:delete` separately (AWS-IAM-style) — produces HTTP 400 at apply. `:delete` is not in the DSL for `settings:objects`.
- Use just `:read` + `:write` and accept that delete capability isn't separately controllable — works, but loses the "full admin" semantic that a `production-admin`-style policy needs.

**Why:** Dumped 133 policies from a real account via `scripts/iam-list.sh`. Token frequency: `settings:objects:read` (135), `settings:objects:write` (102), `settings:objects:admin` (5), **`settings:objects:delete` (0)**. Zero is the conclusive signal. `:admin` is the canonical umbrella verb covering full management including delete. Other services have different verb sets — `app-engine:apps`, `document:documents`, `state:user-app-states`, and others DO have `:delete` tokens — the pattern is per-service, not universal.

**Trade-offs:** `:admin` is broader than just `:delete` — operators who want write-without-delete (or delete-without-write) granularity don't have that option in the `settings:objects` DSL. Workaround: combine with boundaries to restrict scope of admin power.

**Revisit if:** Dynatrace adds finer-grained verbs to `settings:objects` (the existing precedent of `app-engine:apps:delete` shows fine-grained delete IS a thing for other services). Or if the verb namespace changes in a future provider/API release.

---

## 2026-05-18 — Gen 3 documents are a separate namespace from Settings 2.0

**Chosen:** For Dynatrace Gen 3 documents (dashboards, notebooks, segments), use `document:documents:*` tokens in policy `statement_query` strings — NOT `settings:objects:*` with a `WHERE settings:schemaId = "..."` filter. Do not use `WHERE document:type = "dashboard"` style predicates; they are not valid IAM DSL syntax.

**Alternatives:**
- Use `settings:objects:*` + `WHERE settings:schemaId = "..."` and try to find a dashboard schemaId — won't work. Gen 3 dashboards are NOT settings objects; they don't have a settings schemaId. They live in a separate document service.
- Use `document:documents:read/write/delete WHERE document:type = "dashboard"` — original attempt; rejected by the API at apply. The tokens are valid; the WHERE predicate is not.
- Skip dashboards entirely — defeats the use case.

**Why:** Existing policies in real accounts use `document:documents:read`, `document:documents:write`, `document:documents:delete`, `document:documents:admin` — all valid. None of them combine those tokens with a `WHERE document:type` predicate. The Gen 3 IAM model puts document-attribute filtering at the **boundary** layer (via `dynatrace_iam_policy_boundary` queries), not inline in the policy statement. The `terraform/iam/dashboard_edit` example policy now uses the canonical `ALLOW document:documents:read, document:documents:write, document:documents:delete;` pattern (no WHERE), and operators who want narrower-than-all-documents scope are directed to add a boundary.

**Trade-offs:** A policy granting `document:documents:write` grants on ALL documents (dashboards, notebooks, segments, et al.) — not just dashboards. There is currently no mechanism in the DSL to narrow this within the policy itself; the only way to limit scope is via boundary attributes (which are themselves not exhaustively documented and may not support per-document-type predicates either).

**Revisit if:** Dynatrace adds per-type predicates to the IAM DSL, OR introduces sub-namespaces under `document:` (e.g., a hypothetical `document:dashboards:*`). The existing precedent in other services suggests this could happen — `automation` has separate `:automations`, `:calendars`, `:rules`, `:workflows` resources.

---

## 2026-04-16 — Flat Script Directory Structure

**Chosen:** All scripts in a single `scripts/` directory
**Alternatives:** Language-specific subdirectories (`scripts/python/`, `scripts/bash/`)
**Why:** Small number of scripts (4 total). Flat structure keeps paths short and simple for documentation and usage examples.
**Trade-offs:** If PowerShell or additional languages are added, the directory could become crowded.
**Revisit if:** More than 6 scripts exist, or a third language is added.
