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

## 2026-04-16 — Flat Script Directory Structure

**Chosen:** All scripts in a single `scripts/` directory
**Alternatives:** Language-specific subdirectories (`scripts/python/`, `scripts/bash/`)
**Why:** Small number of scripts (4 total). Flat structure keeps paths short and simple for documentation and usage examples.
**Trade-offs:** If PowerShell or additional languages are added, the directory could become crowded.
**Revisit if:** More than 6 scripts exist, or a third language is added.
