# Account-level IAM policies. Each policy is a `statement_query` in
# Dynatrace's permission DSL. Format:
#
#   ALLOW <service:resource:action>[, ...] [WHERE <conditions>];
#
# Confirmed-valid tokens (verified in the dynatrace-oss provider's
# integration tests under dynatrace/api/iam/v2bindings/testcases/):
#   - settings:objects:read
#   - settings:schemas:read
#
# Inferred-valid tokens (follow the :read naming pattern but unverified
# in the provider's own examples):
#   - settings:objects:write
#   - settings:objects:delete
#
# If `terraform apply` returns HTTP 400 on a policy below, the most likely
# cause is an unsupported permission token. Re-run with TF_LOG=DEBUG and
# search for `HTTP/2.0 400` to find Dynatrace's error body, then consult
# the IAM permissions catalog for the canonical token names.
#
# Bindings in bindings.tf attach these policies to groups. Policies and
# bindings must agree on scope — these are all account-level, so the
# corresponding bindings use `account = var.account_uuid`.

resource "dynatrace_iam_policy" "monitoring_read_only" {
  name        = "monitoring-read-only"
  description = "Read-only access to settings objects and schemas"
  account     = var.account_uuid

  statement_query = "ALLOW settings:objects:read, settings:schemas:read;"
}

# The original `dashboard_edit` example used `document:documents:*` tokens
# that Dynatrace rejected at apply (HTTP 400 — unsupported in the IAM DSL).
# Rewritten as a settings-schema-scoped edit policy, defaulting to the
# `builtin:management-zones` schema as a verified-existing placeholder.
# Swap the schemaId to scope to whichever settings schema you actually
# want to grant edit access to (Settings 2.0 schemas are listed at
# /api/v2/settings/schemas on your tenant).
resource "dynatrace_iam_policy" "dashboard_edit" {
  name        = "dashboard-edit"
  description = "Edit a single settings schema (defaults to builtin:management-zones placeholder)"
  account     = var.account_uuid

  statement_query = "ALLOW settings:objects:read, settings:objects:write, settings:objects:delete, settings:schemas:read WHERE settings:schemaId = \"builtin:management-zones\";"
}

# `:write` and `:delete` are inferred from the `:read` pattern but not
# confirmed in the provider's integration tests. If this policy fails to
# create with HTTP 400 after the next apply, drop those tokens (keep just
# `settings:objects:read` and `settings:schemas:read`) and use
# TF_LOG=DEBUG to see Dynatrace's error message.
resource "dynatrace_iam_policy" "production_admin" {
  name        = "production-admin"
  description = "Full settings admin — scope-limited via the production-only boundary"
  account     = var.account_uuid

  statement_query = "ALLOW settings:objects:read, settings:objects:write, settings:objects:delete, settings:schemas:read;"
}
