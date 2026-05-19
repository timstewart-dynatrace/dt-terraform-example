# Dynatrace IAM — Terraform Scaffold

Manage Dynatrace **account-level** IAM with Terraform: user groups, policies, permission boundaries, and bindings.

This is a separate concern from the migration pipelines in the parent repo. The pipelines move **tenant-level** configuration (dashboards, alerting profiles, settings) between environments using tenant tokens. IAM lives at the **account** level, uses different credentials (OAuth client), and targets a different API (`api.dynatrace.com`, not the tenant URL). See [.claude/DECISIONS.md](../../.claude/DECISIONS.md) entry for 2026-05-18 for the rationale.

## What's in here

| File | Purpose |
|---|---|
| `versions.tf` | Terraform and provider version constraints (provider pinned `~> 1.96`) |
| `providers.tf` | Provider block — auth via env vars only |
| `variables.tf` | `account_uuid`, `environment_id`, `management_zone_id` |
| `terraform.tfvars.example` | Template for variable values (copy to `terraform.tfvars`) |
| `groups.tf` | Example: `platform-team`, `dashboard-readers` |
| `policies.tf` | Examples: `monitoring-read-only` (settings read), `dashboard-edit` (settings-schema-scoped edit, defaults to `builtin:management-zones` placeholder), `production-admin` (settings read/write/delete) |
| `boundaries.tf` | Example: `production-only` (restricts a policy to one management zone) |
| `bindings.tf` | Wire groups → policies, with the boundary on `production-admin` |

## Auth model: OAuth client (not tenant tokens)

The IAM Account Management API requires an **OAuth2 bearer token** — raw API tokens (`dt0c01...`) and Platform Tokens (`dt0s16...`) will not work. The Terraform provider exchanges your OAuth client credentials (`DT_CLIENT_ID` + `DT_CLIENT_SECRET`) for a short-lived bearer token automatically on each run; you don't manage bearer tokens yourself, but the OAuth client must carry the right scopes (listed below).

The provider docs state the OAuth-client requirement explicitly per resource — for example, the [dynatrace_iam_group resource (Dynatrace provider docs)](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest/docs/resources/iam_group) requires *"the environment variables `DT_CLIENT_ID`, `DT_CLIENT_SECRET`, `DT_ACCOUNT_ID` with an OAuth client"*.

### Required environment variables

```bash
export DT_CLIENT_ID="dt0s02.XXXXXXXX"
export DT_CLIENT_SECRET="dt0s02.XXXXXXXX.YYYYYYYY"
export DT_ACCOUNT_ID="abc12345-1234-1234-1234-abcdef012345"
```

`DT_ACCOUNT_ID` is your account UUID — the same value you'll put in `terraform.tfvars` as `account_uuid`. The Terraform provider reads it from the env var; the resources also accept it as an HCL argument so the bindings know which account scope to target.

### Required OAuth client scopes

The minimal set for everything in this scaffold:

| Scope | Needed for |
|---|---|
| `account-idm-read` | Read groups and users |
| `account-idm-write` | Create/delete groups |
| `iam-policies-management` | Create/delete policies, boundaries, and bindings |
| `account-env-read` | Resolve environment references — required by the provider for `dynatrace_iam_policy`, `dynatrace_iam_policy_boundary`, and `dynatrace_iam_policy_bindings_v2` per the provider docs (*"View environments (`account-env-read`)"*), even when the policies are account-scoped |

Verify scope names in the OAuth client creation UI — Dynatrace has occasionally renamed scopes between releases.

### Creating the OAuth client

1. Go to **Account Management** ([account.dynatrace.com](https://account.dynatrace.com)) → **Identity & Access Management** → **OAuth clients**
2. Click **Create client**
3. Description: e.g. `terraform-iam-management`
4. Grant the four scopes listed in the table above
5. Save and copy the **Client ID** and **Client secret** — the secret is shown once and cannot be retrieved later
6. Note your **Account UUID** from the URL on `account.dynatrace.com` (8-4-4-4-12 hex format)

Background reading: [OAuth clients (DT docs)](https://docs.dynatrace.com/docs/manage/identity-access-management/access-tokens-and-oauth-clients/oauth-clients).

## Quick start

```bash
cd terraform/iam/

cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your real account_uuid, environment_id, and a real management_zone_id

export DT_CLIENT_ID="..."
export DT_CLIENT_SECRET="..."
export DT_ACCOUNT_ID="..."     # same UUID as account_uuid in terraform.tfvars

terraform init
terraform fmt -check
terraform validate
terraform plan
```

If `plan` looks correct, apply:

```bash
terraform apply
```

State is local (`terraform.tfstate` in this directory) and gitignored. Move to a remote backend (S3, GCS, Terraform Cloud) before sharing this across operators.

## Customizing for your account

Replace example values with your own:

1. **Groups (`groups.tf`)** — Change group names to match your SSO/IdP claim values if you're federating identity. Add or remove groups as needed.

2. **Policies (`policies.tf`)** — The `statement_query` is the Dynatrace permission DSL. Format:

   ```
   ALLOW <service>:<resource>:<action>[, ...] [WHERE <conditions>];
   ```

   For the full catalog of permission strings, see [Manage user permissions: policies (DT docs)](https://docs.dynatrace.com/docs/manage/identity-access-management/permission-management/manage-user-permissions-policies).

3. **Boundaries (`boundaries.tf`)** — A boundary is a `WHERE` clause that gets AND-ed onto a policy at bind time. Common patterns:

   ```
   environment:management-zone = "<mz-id>"
   environment:management-zone startsWith "[Prod]"
   environment:host-tag = "production"
   ```

4. **Bindings (`bindings.tf`)** — One `dynatrace_iam_policy_bindings_v2` per (group, scope) pair. **Read the caveat below before editing**.

## Important caveats

### Permission DSL tokens are validated at apply, not at plan

`terraform validate` checks that `statement_query` is a string with the right HCL shape. It does **not** parse the Dynatrace permission DSL inside the string. The first time Dynatrace sees the query content is during `terraform apply`, and unsupported tokens come back as HTTP 400 with the body stripped by the provider.

Token verb conventions verified by inspecting real policies in a Dynatrace account (see "Discovering valid permission tokens" below):

- **`settings:objects`** — valid verbs: `:read`, `:write`, `:admin`. **No `:delete`** — `:admin` is the umbrella verb covering full management including delete.
- **`document:documents`** — valid verbs: `:read`, `:write`, `:delete`, `:admin`. Documents in Gen 3 (dashboards, notebooks, segments) are a separate namespace from Settings 2.0.
- **Multiple statements** — combine `ALLOW` and `DENY` separated by `;` in a single `statement_query`.
- **WHERE clauses** — support `=`, `IN (...)`, boolean combinations on `settings:schemaId`, `settings:schemaGroup`, `settings:scope`, etc. They do **not** support arbitrary predicates like `document:type = "dashboard"` (Gen 3 document filtering happens at boundary level instead).

If an apply still fails on a policy with `HTTP 400`, re-run with `TF_LOG=DEBUG terraform apply 2>&1 | tee apply.log` and search for `HTTP/2.0 400` to see the actual error body.

### Discovering valid permission tokens

Dynatrace doesn't publish an exhaustive IAM permission catalog at a stable URL — the canonical reference is the set of policies already in your account. Use the diagnostic script bundled with this repo:

```bash
scripts/iam-list.sh                  # writes JSON to /tmp/iam-*.json
scripts/iam-list.sh -o ./out         # custom output directory
```

The script exchanges your OAuth client credentials for a bearer token, fetches groups + policies + boundaries via the Account Management API, and prints a deduplicated list of every `service:resource:action` token used across all your existing policies. That list is your account's canonical IAM DSL vocabulary — copy verb conventions from it before writing new policies.

## Bulk export existing IAM resources as HCL

To bring existing IAM resources (groups, policies, boundaries, bindings) under Terraform management, use the `dynatrace-oss/dynatrace` provider's built-in export utility via the bundled wrapper:

```bash
scripts/iam-export.sh
```

This:

1. Locates the `terraform-provider-dynatrace` binary inside `terraform/iam/.terraform/providers/...` (so `terraform init` must have been run first)
2. Runs the export utility against the four standard IAM resource types (`dynatrace_iam_group`, `dynatrace_iam_policy`, `dynatrace_iam_policy_boundary`, `dynatrace_iam_policy_bindings_v2`)
3. Writes generated HCL files to `exported-iam/` at the repo root (override with `-o`)

IAM is excluded from the default export — per the provider's own `-list-exclusions` output, *"Account management requires OAuth2 client and is specific to SaaS"* — so the script names the resources explicitly. To include other types:

```bash
scripts/iam-export.sh dynatrace_iam_user dynatrace_iam_service_user dynatrace_iam_permission
```

To inspect everything the provider considers excluded:

```bash
# From terraform/iam/ after `terraform init`
.terraform/providers/registry.terraform.io/dynatrace-oss/dynatrace/*/*/terraform-provider-dynatrace_v* \
  -export -list-exclusions
```

### What the exported output is and isn't

The generated `.tf` files are a **starting point**, not a drop-in replacement for the existing scaffold:

- They describe your current account state at export time — copy them into a working tree and add `versions.tf` + `providers.tf` before running `terraform plan`
- They do **not** populate Terraform state — every exported resource is foreign to your local state. To take over management, `terraform import <address> <id>` each one you want managed
- The `-id` flag (which `iam-export.sh` enables) writes the source `id` as an HCL comment in each resource block to make `import` commands easier to script
- If you want state population in the same step, swap the `-flat -id` flags for `-import-state` in the script (read the provider's export docs first — `-import-state` is opinionated about target module structure)

The export is also a **point-in-time** snapshot — running it twice produces fresh files, not incremental diffs. Treat it as a discovery tool, not a sync mechanism.

### Bindings re-assign all policies — list every policy that should remain

Per the [dynatrace_iam_policy_bindings_v2 resource (Dynatrace provider docs)](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest/docs/resources/iam_policy_bindings_v2), this resource *"re-assigns all policies bound to a group, so every policy that should remain bound must be specified in the configuration; otherwise, it will be unbound."* If you remove a `policy` block from a bindings_v2 resource, that policy is unbound from the group at the next apply. There is also a brief window during apply where the group has zero policies attached — plan apply timing accordingly for production.

### Deprecated arguments (kept out of this scaffold)

The current provider version flags two deprecations relevant here:

- `dynatrace_iam_group.permissions` block — deprecated in favor of `dynatrace_iam_permission` resources and policy bindings. This scaffold uses bindings; do not re-add a `permissions` block to the group resources.
- `dynatrace_iam_policy.environment` argument — deprecated in favor of `account`-scoped policies. All example policies here use `account = var.account_uuid`.

### Verify against the current provider release before apply

Argument names on IAM resources have shifted between provider releases. This scaffold was written against provider v1.96.0. Before applying after a provider bump:

1. Run `terraform init -upgrade` and note the resolved version
2. Open the [dynatrace-oss/dynatrace provider releases (GitHub)](https://github.com/dynatrace-oss/terraform-provider-dynatrace/releases) and read the notes for every version between the pinned one and the new one
3. Check the registry docs for each IAM resource you use — argument names, deprecations, new required fields
4. Re-run `terraform plan` and confirm the diff is what you expect

## Validation commands

```bash
terraform fmt -check     # exits non-zero if any .tf file is not canonically formatted
terraform validate       # syntax + schema check, no API calls
terraform plan           # full diff against current account state (uses OAuth)
```

## Handoff notes (for an agent picking this up cold)

This subsystem was built and stabilized across PRs #17–#21. Here's what you need to know to extend it without re-walking the same wall.

### What's applied

A successful `terraform apply` against a real Dynatrace account left these 8 resources in state:

- 2 groups (`platform-team`, `dashboard-readers`)
- 1 boundary (`production-only`, scoping to `var.management_zone_id`)
- 3 policies (`monitoring-read-only`, `dashboard-edit`, `production-admin`)
- 2 bindings (`platform_team_admin` with the production boundary, `dashboard_readers` without)

State is local (`terraform.tfstate` in this directory, gitignored). Move to a remote backend before another operator joins.

### How DSL token discovery works

Dynatrace does **not** publish a stable IAM permission catalog. The provider's documented examples only cover `settings:objects:read` / `settings:schemas:read`. The Dynatrace docs landing pages reference a catalog but no URL points at one.

**The pattern that works:** dump existing policies from an account and read their `statementQuery` strings. The account's own vocabulary is authoritative. Use [`scripts/iam-list.sh`](../../scripts/iam-list.sh) — it does the OAuth bearer-token exchange, GETs all policies, and prints a deduplicated token list. Treat its output as the DSL reference before writing any new policy.

### Token gotchas already proved by HTTP 400

| Wrong | Right | Why |
|---|---|---|
| `settings:objects:delete` | `settings:objects:admin` | `:delete` is not in the DSL for `settings:objects`. `:admin` is the umbrella verb. |
| `document:documents:write WHERE document:type = "dashboard"` | `document:documents:write` (no WHERE) | The tokens are valid. The `WHERE document:type = "..."` predicate isn't supported. Use a boundary for scope. |
| `entities:read`, `davis-problems:read` | dump existing policies and find equivalents | Not in the DSL. Real names use service prefixes like `storage:entities:read` or similar. |

See [.claude/DECISIONS.md](../../.claude/DECISIONS.md) entries dated 2026-05-18 for the full reasoning.

### Known open items

1. **`dashboard-edit` is broader than its name.** With `document:documents:read/write/delete` and no WHERE, it grants on all Gen 3 documents (dashboards, notebooks, segments). For narrower scope, write a boundary that filters on document attributes — boundary syntax beyond `environment:management-zone` is not well documented, so confirm against existing boundaries (`scripts/iam-list.sh` dumps these too) before writing one.

2. **`production-admin`'s boundary depends on `var.management_zone_id`.** If the value in `terraform.tfvars` is the placeholder (`REPLACE_WITH_REAL_MZ_ID`), the boundary applies to no MZ and the admin policy effectively has no scope restriction.

3. **CHANGELOG `[Unreleased]` has 5 PRs of accumulated changes.** Following the project's pattern (see [.claude/rules/core.md](../../.claude/rules/core.md)), cut a `chore: release 0.4.0` commit at a natural pause to finalize the section with a date and create the git tag.

4. **No tests.** `terraform fmt -check` and `terraform validate` are the only local checks. A future CI job for `terraform validate` on `terraform/iam/` would prevent broken HCL from landing — currently the pytest matrix doesn't cover this directory.

5. **Existing account IAM not yet imported.** The account has 130+ pre-existing policies that this scaffold doesn't manage. To bring them under Terraform: run `scripts/iam-export.sh` (generates HCL into `exported-iam/`), select the ones worth managing, `terraform import` each, then add to a working tree.

### Suggested next-agent workflow

If asked to extend IAM:

1. Read this README, then `.claude/DECISIONS.md` (2026-05-18 entries), then `policies.tf` for the canonical token examples
2. Run `scripts/iam-list.sh` against the target account — get the live DSL vocabulary
3. Write the new policy / boundary / binding in HCL using only tokens that appear in step 2's output
4. `terraform plan` first; expect HTTP 400 at apply if a guessed token slipped through — re-run with `TF_LOG=DEBUG terraform apply` to see the actual error body
5. Update this README and `.claude/DECISIONS.md` with anything new you learn

## References

- [dynatrace-oss/dynatrace provider (Terraform Registry)](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest)
- [dynatrace_iam_group resource (Dynatrace provider docs)](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest/docs/resources/iam_group)
- [dynatrace_iam_policy resource (Dynatrace provider docs)](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest/docs/resources/iam_policy)
- [dynatrace_iam_policy_boundary resource (Dynatrace provider docs)](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest/docs/resources/iam_policy_boundary)
- [dynatrace_iam_policy_bindings_v2 resource (Dynatrace provider docs)](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest/docs/resources/iam_policy_bindings_v2)
- [Manage user permissions: policies (DT docs)](https://docs.dynatrace.com/docs/manage/identity-access-management/permission-management/manage-user-permissions-policies)
- [OAuth clients (DT docs)](https://docs.dynatrace.com/docs/manage/identity-access-management/access-tokens-and-oauth-clients/oauth-clients)
