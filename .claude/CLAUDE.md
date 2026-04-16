# Dynatrace Terraform Migration Tools

**ALWAYS** ask clarifying questions and **ALWAYS** provide a plan **BEFORE** making changes to ensure the end result matches intent.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

Standalone tools for Dynatrace configuration migration between tenants using Terraform-compatible workflows. Provides Python and Shell scripts for source export, validation, backup, and target deployment. Built for Dynatrace administrators who need reliable, safe configuration migration between tenants.

**Last Updated:** 2026-04-16

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Runtime | Python 3.8+ / Bash 4.0+ | Cross-platform scripting |
| IaC Tool | Terraform CLI 1.5+ | Dynatrace configuration-as-code |
| HTTP | requests 2.31+ | API calls to Dynatrace tenants |
| Config | PyYAML 6.0+ | Environment configuration |
| Env Mgmt | python-dotenv 1.0+ | Secure credential management via .env files |
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

## Current Phase

Before starting work, check `.claude/phases/` for the active phase.
- Active Phase: See `PHASE-01-active.md` (or current phase)
- Track: Append decisions to `DECISIONS.md` as you go
- When Done: Rename to `PHASE-01-done.md`, create `PHASE-02-active.md`

Detailed phase management rules: @.claude/rules/core.md

## Rules

### Always active
@.claude/rules/core.md
@.claude/rules/development.md
@.claude/rules/testing.md
@.claude/rules/deployment.md
@.claude/rules/python.md

### Debugging & Troubleshooting
@.claude/rules/debugging.md
@.claude/rules/existing-code.md

## Skills

### Terraform Provider & HCL Resources
@/Users/Shared/GitHub/PROJECTS/VisualCode-AI-Template/SKILLS/dynatrace-terraform/SKILL.md

### Dynatrace Platform APIs
@/Users/Shared/GitHub/PROJECTS/VisualCode-AI-Template/SKILLS/dynatrace-apis/SKILL.md

## Decision Log

See `.claude/DECISIONS.md` to track architectural and technical decisions.
