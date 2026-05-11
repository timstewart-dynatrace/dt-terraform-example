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

## 2026-04-16 — Flat Script Directory Structure

**Chosen:** All scripts in a single `scripts/` directory
**Alternatives:** Language-specific subdirectories (`scripts/python/`, `scripts/bash/`)
**Why:** Small number of scripts (4 total). Flat structure keeps paths short and simple for documentation and usage examples.
**Trade-offs:** If PowerShell or additional languages are added, the directory could become crowded.
**Revisit if:** More than 6 scripts exist, or a third language is added.
