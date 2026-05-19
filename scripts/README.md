# Legacy Migration Scripts

These scripts provide a single-step migration workflow that combines export and deploy into one operation. For production use with code review and format flexibility, see the [pipeline system](../pipelines/) instead.

## Scripts

### migrate.py

All-in-one Python migration. Exports configuration from a source tenant via the Dynatrace API, generates Terraform-compatible output, and deploys to a target tenant.

**Workflow:** verify Terraform CLI -> create environments.yaml -> verify API connections -> backup target -> download source -> validate -> generate Terraform config -> deploy

```bash
# Using .env
source .env
python3 scripts/migrate.py

# With arguments
python3 scripts/migrate.py \
    --source https://source.live.dynatrace.com \
    --target https://target.live.dynatrace.com \
    --source-token TOKEN \
    --target-token TOKEN

# Dry run
python3 scripts/migrate.py --dry-run

# Specific types only
python3 scripts/migrate.py --config-types dashboard,management-zone

# List supported types
python3 scripts/migrate.py --list-types
```

| Flag | Description |
|------|-------------|
| `--source` | Source tenant URL (or `SOURCE_TENANT_URL` env var) |
| `--target` | Target tenant URL (or `TARGET_TENANT_URL` env var) |
| `--source-token` | Source API token (or `SOURCE_TENANT_TOKEN` env var) |
| `--target-token` | Target API token (or `TARGET_TENANT_TOKEN` env var) |
| `--config-dir` | Working directory for configs (default: `config`) |
| `--dry-run` | Run terraform plan only, skip apply |
| `--config-types` | Comma-separated list of types to migrate |
| `--list-types` | Print available config types and exit |

---

### migrate.sh

Shell equivalent of `migrate.py`. Same 7-step workflow with colored terminal output.

```bash
# Using .env
source .env
./scripts/migrate.sh

# With arguments
./scripts/migrate.sh \
    --source-url https://source.live.dynatrace.com \
    --target-url https://target.live.dynatrace.com \
    --source-token TOKEN \
    --target-token TOKEN

# Dry run
./scripts/migrate.sh --dry-run

# Skip target backup
./scripts/migrate.sh --no-backup

# Specific types
./scripts/migrate.sh --config-types dashboard,management-zone

# List types
./scripts/migrate.sh --list-types
```

| Flag | Description |
|------|-------------|
| `--source-url` | Source tenant URL |
| `--target-url` | Target tenant URL |
| `--source-token` | Source API token |
| `--target-token` | Target API token |
| `--config-dir` | Working directory for configs (default: `config`) |
| `--dry-run` | Preview changes without applying |
| `--no-backup` | Skip backup of target configuration |
| `--config-types` | Comma-separated list of types to migrate |
| `--list-types` | Print available config types and exit |

---

### clone-config.sh

Standalone helper that downloads configuration from a single tenant into a timestamped directory. No deployment — export only.

```bash
# All config types
./scripts/clone-config.sh https://tenant.live.dynatrace.com TOKEN

# Specific types
./scripts/clone-config.sh https://tenant.live.dynatrace.com TOKEN dashboard,management-zone
```

| Argument | Required | Description |
|----------|----------|-------------|
| `source-url` | Yes | Dynatrace tenant URL |
| `source-token` | Yes | API token |
| `config-types` | No | Comma-separated types (default: all) |

Output directory: `config/cloned-YYYYMMDD-HHMMSS/`

---

### verify_migration.py

Post-migration verification that compares configuration counts between source and target tenants. Reports pass/warn/fail per config type.

```bash
# Using .env
source .env
python3 scripts/verify_migration.py

# With arguments
python3 scripts/verify_migration.py \
    --source https://source.live.dynatrace.com \
    --target https://target.live.dynatrace.com \
    --source-token TOKEN \
    --target-token TOKEN
```

| Flag | Description |
|------|-------------|
| `--source` | Source tenant URL (or `SOURCE_TENANT_URL` env var) |
| `--target` | Target tenant URL (or `TARGET_TENANT_URL` env var) |
| `--source-token` | Source API token (or `SOURCE_TENANT_TOKEN` env var) |
| `--target-token` | Target API token (or `TARGET_TENANT_TOKEN` env var) |

Checks: dashboards, alerting profiles, management zones, notifications, auto-tags.

---

### iam-list.sh

Diagnostic for the **account-level IAM subsystem** at [`terraform/iam/`](../terraform/iam/) — NOT for the migration pipelines. Uses different auth (OAuth client, not tenant tokens).

Exchanges OAuth client credentials for a bearer token, then GETs groups, policies, and boundaries from the Account Management API at `api.dynatrace.com`. Writes raw JSON to an output directory and prints a deduplicated list of every `service:resource:action` permission token used across the account's existing policies. **The token list is the canonical IAM DSL vocabulary** — Dynatrace does not publish this catalog publicly, so an account's existing policies are the authoritative reference.

```bash
# Required env vars: DT_CLIENT_ID, DT_CLIENT_SECRET, DT_ACCOUNT_ID
./scripts/iam-list.sh                  # writes to /tmp/iam-*.json
./scripts/iam-list.sh -o ./iam-dump    # custom output directory
```

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Output directory for JSON files (default: `/tmp`) |
| `-h`, `--help` | Show usage |

Output files:
- `iam-groups.json` — all groups in the account
- `iam-policies-list.json` — policy summaries (may not include `statementQuery`)
- `iam-policies-detail.json` — full details for every policy with `statementQuery`
- `iam-boundaries.json` — boundary list

Required OAuth scopes: `account-idm-read`, `iam-policies-management`, `account-env-read`.

Credentials may be exported in the shell OR placed in `.env` at the repo root — the script auto-sources `.env` if it exists.

---

### iam-export.sh

Wrapper around the `dynatrace-oss/dynatrace` provider's built-in `-export` utility, specialized for IAM. IAM resources are excluded from the default export (the provider's `-list-exclusions` documents this as *"Account management requires OAuth2 client and is specific to SaaS"*), so the wrapper names the four standard IAM resource types explicitly. Generates HCL for current account state — useful for bringing UI-created IAM under Terraform management.

```bash
# Required env vars: DT_CLIENT_ID, DT_CLIENT_SECRET, DT_ACCOUNT_ID
# Prerequisite: terraform init must have run in terraform/iam/
./scripts/iam-export.sh                                       # default 4 IAM types
./scripts/iam-export.sh dynatrace_iam_user                    # add extras
./scripts/iam-export.sh -o /tmp/iam-out                       # custom output dir
```

| Flag / arg | Description |
|------|-------------|
| `-o`, `--output` | Output directory for `.tf` files (default: `exported-iam/` at repo root) |
| `extra_resource_type` | Append additional resource type names (e.g. `dynatrace_iam_user`, `dynatrace_iam_permission`) |
| `-h`, `--help` | Show usage |

Default resources: `dynatrace_iam_group`, `dynatrace_iam_policy`, `dynatrace_iam_policy_boundary`, `dynatrace_iam_policy_bindings_v2`.

Credentials and the required `DYNATRACE_ENV_URL` may be exported in the shell OR placed in `.env` at the repo root — the script auto-sources `.env` if it exists. `DYNATRACE_ENV_URL` falls back to `SOURCE_TENANT_URL` then `TARGET_TENANT_URL` from the migration pipeline config.

**The generated `.tf` files do NOT populate Terraform state.** To take over management of a generated resource: copy the block into a working tree, add `versions.tf` + `providers.tf`, then `terraform import <addr> <id>` (source `id` is included as a comment via the `-id` flag). The export is point-in-time — not a sync mechanism.

To see every resource type the provider excludes from default export:

```bash
cd terraform/iam/
.terraform/providers/registry.terraform.io/dynatrace-oss/dynatrace/*/*/terraform-provider-dynatrace_v* \
  -export -list-exclusions
```

---

## Setup Wizard

`setup.sh` lives in the project root (not in `scripts/`). It's an interactive wizard that checks dependencies, collects tenant credentials, verifies API connectivity, and writes a `.env` file.

```bash
./setup.sh
```
