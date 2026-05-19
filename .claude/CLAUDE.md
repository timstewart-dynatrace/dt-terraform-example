# Dynatrace Terraform Migration Tools

**ALWAYS** ask clarifying questions and **ALWAYS** provide a plan **BEFORE** making changes to ensure the end result matches intent.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

Standalone tools for Dynatrace configuration migration between tenants using Terraform-compatible workflows. Provides Python and Shell scripts for source export, validation, backup, and target deployment. Built for Dynatrace administrators who need reliable, safe configuration migration between tenants.

**Last Updated:** 2026-05-11

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Runtime | Python 3.8+ / Bash 4.0+ | Cross-platform scripting |
| IaC Tool | Terraform CLI 1.5+ | Dynatrace configuration-as-code |
| HTTP | requests 2.31+ | API calls to Dynatrace tenants |
| Config | PyYAML 6.0+ | Environment configuration |
| Env Mgmt | python-dotenv 1.0+ | Secure credential management via .env files |
| Output | tabulate 0.9+ | Formatted table output for pipeline reports |
| Utilities | curl, jq | Shell-based API interaction and JSON processing |

## Architecture

See [architecture.md](architecture.md) for project structure, components, and data flow.

## Essential Commands

```bash
# Setup
cp config/.env.example .env
nano .env  # Add tenant URLs and tokens
source .env
pip install -r requirements.txt

# Run Migration (Python)
python3 scripts/migrate.py

# Run Migration (Shell)
./scripts/migrate.sh

# Dry Run
python3 scripts/migrate.py --dry-run
./scripts/migrate.sh --dry-run

# Selective Migration
python3 scripts/migrate.py --config-types dashboard,alerting-profiles

# List Supported Config Types
python3 scripts/migrate.py --list-types
./scripts/migrate.sh --list-types

# Clone Configuration
./scripts/clone-config.sh

# Verify Migration
python3 scripts/verify_migration.py
```

## IAM Subsystem (`terraform/iam/`)

The repo has **two distinct concerns** in two subtrees that **do not share auth, code, or state**:

1. **Migration pipelines** (`pipelines/`, `scripts/migrate.*`) — tenant-level configuration migration. Authenticates with **tenant tokens** (Platform Token `dt0s16` or classic API Token `dt0c01`) against `<tenant>.live.dynatrace.com`. See the rest of this CLAUDE.md.

2. **IAM as code** (`terraform/iam/`) — account-level IAM (groups, policies, permission boundaries, bindings). Authenticates with **OAuth client credentials** (`DT_CLIENT_ID` / `DT_CLIENT_SECRET` / `DT_ACCOUNT_ID`) against `api.dynatrace.com`. **Cannot use tenant tokens** — IAM is account-level and the API rejects them.

### Critical facts for an agent extending IAM work

- **No public permission catalog.** Dynatrace does not publish the IAM permission DSL (`service:resource:action` tokens) at a stable URL. The canonical reference is **existing policies in the operator's account** — dump them with [`scripts/iam-list.sh`](scripts/iam-list.sh) and read the deduplicated token list. Do this before writing any new `statement_query`.
- **`settings:objects:delete` does not exist.** Verified from a 133-policy dump (0 occurrences). Use `settings:objects:admin` as the umbrella verb for full management. `settings:objects` valid verbs: `:read`, `:write`, `:admin`.
- **Gen 3 documents are a separate namespace.** Dashboards, notebooks, segments live in `document:documents:*`, not `settings:objects:*`. The DSL does **not** support `WHERE document:type = "dashboard"` style predicates — narrow scope via boundaries on document attributes instead.
- **Bindings re-assign everything.** `dynatrace_iam_policy_bindings_v2` overwrites all policies on a (group, scope) tuple on every apply. Every policy that should remain bound must be in the config.
- **`terraform validate` doesn't catch DSL errors.** `statement_query` is just a string to Terraform. Real validation happens server-side at apply time as HTTP 400. The provider strips the response body — re-run with `TF_LOG=DEBUG` to see Dynatrace's actual error message.

### Tooling for IAM work

- [`scripts/iam-list.sh`](scripts/iam-list.sh) — dump existing groups / policies / boundaries to `/tmp/iam-*.json` plus a deduplicated permission-token list (the DSL Rosetta Stone for an account)
- [`scripts/iam-export.sh`](scripts/iam-export.sh) — wrapper around the provider's `-export` utility, specialized for IAM (excluded by default). Generates HCL for existing account state into `exported-iam/` at the repo root. Output is a discovery starting point, not a sync mechanism.
- [`terraform/iam/README.md`](terraform/iam/README.md) — operator-facing docs: OAuth client setup, scope reference, scaffold layout, caveats, handoff notes

## Current Phase

Before starting work, check `.claude/phases/` for the active phase.
- Completed: `PHASE-01-done.md` (best-practices conformance), `PHASE-02-done.md` (combined auth + dependency refresh), `PHASE-03-done.md` (pytest coverage + CI), `PHASE-04-done.md` (Reference Currency directive + URL liveness validator)
- Active: `PHASE-05-active.md` (test coverage expansion — deploy/export pipelines + validator script)
- Track: Append decisions to `DECISIONS.md` as you go
- When done: Rename `active` to `done`, create next phase

Detailed phase management rules: @.claude/rules/core.md

## Rules

### Always active
@.claude/rules/core.md
@.claude/rules/development.md
@.claude/rules/testing.md
@.claude/rules/deployment.md
@.claude/rules/python.md
@.claude/rules/reference-currency.md

### Debugging & Troubleshooting
@.claude/rules/debugging.md
@.claude/rules/existing-code.md

## Skills

### Terraform Provider & HCL Resources
@/Users/Shared/GitHub/CLAUDE/Claude-AI-Template/SKILLS/dynatrace-terraform/SKILL.md

### Monaco CLI & Tenant Migration
@/Users/Shared/GitHub/CLAUDE/Claude-AI-Template/SKILLS/dynatrace-monaco/SKILL.md

### Dynatrace Platform APIs
@/Users/Shared/GitHub/CLAUDE/Claude-AI-Template/SKILLS/dynatrace-apis/SKILL.md

### SVG Diagrams & Documentation Graphics
@/Users/Shared/GitHub/CLAUDE/Claude-AI-Template/SKILLS/svg-graphics/SKILL.md

## Decision Log

See `.claude/DECISIONS.md` to track architectural and technical decisions.
