# Exporting Dynatrace IAM as Terraform — Manual Guide

A step-by-step procedure for bulk-exporting **account-level** Dynatrace IAM (groups, policies, permission boundaries, policy bindings) into Terraform HCL files. This guide assumes no automation — just you, a terminal, the Terraform CLI, and the official `dynatrace-oss/dynatrace` provider.

After following this guide you will have:

- One `.tf` file per IAM resource that exists in your Dynatrace account
- A directory you can copy into a Terraform working tree to bring those resources under Terraform management

---

## Why this works

The `dynatrace-oss/dynatrace` provider ships with a built-in **export utility** that is invoked by running the provider's compiled binary directly — not via `terraform <subcommand>`. The utility reads your existing Dynatrace account state via the Account Management API and writes equivalent HCL to a directory.

By default, IAM resources are **excluded** from export — per the provider's own `-list-exclusions` output, *"Account management requires OAuth2 client and is specific to SaaS"*. To export IAM you must name the resources explicitly.

---

## Prerequisites

- **Terraform CLI** 1.5 or later — verify with `terraform --version`
- **A Dynatrace SaaS account** you have admin access to (this does not work for Managed deployments)
- A terminal on macOS, Linux, or WSL
- Roughly 50 MB of disk space (the provider binary is large; exported files are tiny)

---

## Step 1 — Create an OAuth client

The IAM Account Management API requires an **OAuth2 bearer token**. Raw API tokens (`dt0c01...`) and Platform Tokens (`dt0s16...`) will **not** work for IAM. The Terraform provider exchanges OAuth client credentials for a short-lived bearer token automatically; you only need to provide the client ID + secret + account UUID.

1. Open `https://account.dynatrace.com` in your browser
2. Navigate to **Identity & Access Management** → **OAuth clients** → **Create client**
3. Description: anything memorable, e.g. `terraform-iam-export`
4. Grant these scopes (verify exact spelling in the UI — Dynatrace has renamed scopes in past releases):
   - `account-idm-read` — read groups
   - `iam-policies-management` — read policies, boundaries, bindings
   - `account-env-read` — resolve environment references (required by the provider even when the resources are account-scoped)
5. Click **Create**
6. **Copy the Client ID and Client Secret immediately** — the secret is shown once and cannot be retrieved later. Store them in a password manager or secret vault.
7. Note your **Account UUID** — visible in your browser's URL on `account.dynatrace.com`. Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (8-4-4-4-12 hex).

---

## Step 2 — Download the provider binary via `terraform init`

The export utility lives inside the compiled provider binary. The cleanest way to get it on disk is to let Terraform download it for you.

1. Create a working directory:

   ```bash
   mkdir -p ~/dt-iam-export
   cd ~/dt-iam-export
   ```

2. Create a `versions.tf` file with the provider version pinned:

   ```hcl
   terraform {
     required_version = ">= 1.5"
     required_providers {
       dynatrace = {
         source  = "dynatrace-oss/dynatrace"
         version = "~> 1.96"
       }
     }
   }

   provider "dynatrace" {}
   ```

3. Initialize Terraform — this downloads the provider:

   ```bash
   terraform init
   ```

   Expected output ends with `Terraform has been successfully initialized!`. The provider binary is now at:

   ```
   .terraform/providers/registry.terraform.io/dynatrace-oss/dynatrace/<version>/<os_arch>/terraform-provider-dynatrace_v<version>
   ```

   On macOS arm64 with provider v1.96.0 the path is `.terraform/providers/registry.terraform.io/dynatrace-oss/dynatrace/1.96.0/darwin_arm64/terraform-provider-dynatrace_v1.96.0`. On Linux x86_64 it's `linux_amd64`. Substitute appropriately.

---

## Step 3 — Confirm IAM is excluded by default (and see all exclusions)

Run the provider binary with `-export -list-exclusions` to see what's excluded from default export and why:

```bash
.terraform/providers/registry.terraform.io/dynatrace-oss/dynatrace/*/*/terraform-provider-dynatrace_v* \
  -export -list-exclusions
```

You'll see a section titled *"Account management requires OAuth2 client and is specific to SaaS"* listing the IAM resource types:

```
dynatrace_iam_user
dynatrace_iam_group
dynatrace_iam_permission
dynatrace_iam_policy
dynatrace_iam_policy_bindings
dynatrace_iam_policy_bindings_v2
dynatrace_iam_policy_boundary
```

You will export these explicitly in Step 5.

---

## Step 4 — Set environment variables

The export utility reads credentials from environment variables. Set them in your current shell:

```bash
export DT_CLIENT_ID="dt0s02.XXXXXXXX"
export DT_CLIENT_SECRET="dt0s02.XXXXXXXX.YYYYYYYY"
export DT_ACCOUNT_ID="abc12345-1234-1234-1234-abcdef012345"

# The export utility requires this at startup even for IAM-only runs
# (provider initialization quirk; the URL isn't actually used for IAM
# API calls). Use any valid tenant URL from your account.
export DYNATRACE_ENV_URL="https://your-tenant.live.dynatrace.com"
```

Substitute your real values from Step 1. If your tenant is a Gen 3 environment on `.apps.dynatrace.com`, use that URL — the export utility just needs *something* well-formed here.

To avoid having these in your shell history, put them in a file and `source` it:

```bash
cat > ~/.dt-iam-export.env <<'EOF'
export DT_CLIENT_ID="..."
export DT_CLIENT_SECRET="..."
export DT_ACCOUNT_ID="..."
export DYNATRACE_ENV_URL="..."
EOF
chmod 600 ~/.dt-iam-export.env
source ~/.dt-iam-export.env
```

---

## Step 5 — Run the export

From the directory where you ran `terraform init`:

```bash
.terraform/providers/registry.terraform.io/dynatrace-oss/dynatrace/*/*/terraform-provider-dynatrace_v* \
  -export -flat -id \
  dynatrace_iam_group \
  dynatrace_iam_policy \
  dynatrace_iam_policy_boundary \
  dynatrace_iam_policy_bindings_v2
```

### What the flags do

- `-export` — switch the binary into export mode (instead of normal provider operation)
- `-flat` — write all resources into one directory, with no nested module structure (easier to review)
- `-id` — write each source resource's UUID as an HCL comment inside the file. Crucial later when you import resources into Terraform state.

### What the resource names do

You pass one or more resource type names as positional arguments. Without arguments, the utility exports the default (non-excluded) set, which **does not include IAM**. By naming the four IAM types, you opt them in.

You can also add:

- `dynatrace_iam_user` — federated and local users
- `dynatrace_iam_permission` — group permission blocks (deprecated form; usually replaced by policy bindings)
- `dynatrace_iam_policy_bindings` — V1 bindings (deprecated; current is v2)

### Expected runtime

For an account with ~100 groups and ~150 policies, the export takes 30–90 seconds. You will see lines like:

```
Downloading "dynatrace_iam_policy_boundary" Count:  24
Downloading "dynatrace_iam_group" Count:  109
Downloading "dynatrace_iam_policy" Count:  145
Downloading "dynatrace_iam_policy_bindings_v2" Count:  122
Post-Processing Resources ...
...
Finishing touches ...
Writing ___datasources___.tf
Writing ___variables___.tf
Writing main ___providers___.tf
Finish Export ...
... finished after 47 seconds
```

### Where the output goes

The utility writes to `./.configuration/` relative to the current working directory by default. To change that, set `DYNATRACE_TARGET_FOLDER` before invoking:

```bash
export DYNATRACE_TARGET_FOLDER="$HOME/dt-iam-export-output"
```

---

## Step 6 — Review the output

Look at what got generated:

```bash
ls -la .configuration/   # or wherever DYNATRACE_TARGET_FOLDER points
```

You'll find:

- One `.tf` file per resource (named after the resource's name or UUID)
- `___datasources___.tf` — provider-generated data block references
- `___variables___.tf` — variable declarations for IDs that the export couldn't resolve
- `___providers___.tf` — provider block

Open a few of the resource files. Each one looks like:

```hcl
# id = "abc12345-...-..."     <-- the source UUID in a comment (because of -id)
resource "dynatrace_iam_group" "my_group" {
  name        = "my-group"
  description = "Some group"
}
```

The `id =` comment is your reference for `terraform import` in the next step.

---

## Step 7 — Decide what to bring under Terraform management

The exported files describe your account state **at the moment of export**. They do not populate Terraform state, and they don't include a `versions.tf` or full `providers.tf` ready for `terraform apply`. To start managing a resource with Terraform:

1. **Pick which resources you want to manage.** Not all of them — service accounts, deprecated bindings, ad-hoc test groups are often not worth keeping in state.
2. **Copy the resource blocks you want into a working Terraform tree.** This can be the same directory you used for `terraform init`, or a new one. Add a real `providers.tf` if needed (auth via the same env vars).
3. **Import each resource into state** with `terraform import <terraform_address> <source_id>`, where:
   - `<terraform_address>` is the resource block address — e.g. `dynatrace_iam_group.my_group`
   - `<source_id>` is the UUID from the `# id =` comment (or the full `id` field if present)
4. **Run `terraform plan`.** If the import worked, the plan should show "No changes" — Terraform sees the resource in state matching the resource in code.
5. **From then on, the resource is yours to manage.** Edits in HCL → `terraform apply`. Changes made in the Dynatrace UI will show up as drift in the next `terraform plan`.

### Import is one-at-a-time and tedious

There is no `terraform import-all` command. For 100+ resources, write a shell loop that reads each file's `# id =` comment and runs `terraform import`. The `-id` flag exists specifically to make this scriptable. Example pattern:

```bash
for tf_file in *.tf; do
  resource_block=$(grep -E '^resource "[^"]+" "[^"]+"' "$tf_file" | head -1 | awk -F'"' '{print $2"."$4}')
  source_id=$(grep -E '^# id =' "$tf_file" | head -1 | sed -E 's/.*= *"([^"]+)".*/\1/')
  if [ -n "$resource_block" ] && [ -n "$source_id" ]; then
    terraform import "$resource_block" "$source_id"
  fi
done
```

Test this on a single file first. Some resources have compound IDs (UUID + account UUID joined by `#-#`) — those need the full compound string from the source `id`, not just the UUID.

---

## Caveats

- **The export is point-in-time.** Re-running produces fresh files, not incremental diffs. It's not a sync mechanism.
- **Statement queries are exported verbatim.** The DSL strings (e.g. `ALLOW settings:objects:read, settings:schemas:read;`) are copied as-is. After import, future `terraform plan` runs will diff them as plain strings — any whitespace or capitalization changes Dynatrace makes server-side will show up as drift.
- **Bindings re-assign all policies on apply.** Once you bring a `dynatrace_iam_policy_bindings_v2` resource under Terraform management, every subsequent apply re-asserts the full policy list. If someone adds a policy via the UI, your next apply will remove it. This is a Dynatrace API behavior, not a Terraform one.
- **Provider versions matter.** IAM resource argument names have shifted across provider releases. Pin a specific version in `versions.tf` (`~> 1.96` is current as of this writing) and only bump deliberately, after reading release notes.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `No Environment URL has been specified` | `DYNATRACE_ENV_URL` not set. The provider requires this at startup even for IAM-only exports. |
| `401 Unauthorized` during download | OAuth client credentials wrong, or the client lacks one of the three required scopes. |
| `Count: 0` for all resource types | OAuth client has API access but lacks read permissions on the resource. Check the scope list. |
| Export hangs or times out | Account-management API rate-limit. Wait 5 minutes and retry. |
| Generated files have lots of `# REQUIRES MANUAL ATTENTION` comments | The resource references something the export couldn't resolve (cross-environment references, deleted dependencies). Review and clean up manually. |

---

## References

- [dynatrace-oss/dynatrace provider (Terraform Registry)](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest)
- [Provider export utility docs (Dynatrace docs)](https://docs.dynatrace.com/docs/deliver/configuration-as-code/terraform/terraform-cli-commands#export-configuration-from-a-dynatrace-environment-using-the-dynatrace-terraform-provider)
- [OAuth clients (Dynatrace docs)](https://docs.dynatrace.com/docs/manage/identity-access-management/access-tokens-and-oauth-clients/oauth-clients)
- [Manage user permissions: policies (Dynatrace docs)](https://docs.dynatrace.com/docs/manage/identity-access-management/permission-management/manage-user-permissions-policies)
