# Account-level IAM policies. Each policy is a `statement_query` in
# Dynatrace's permission DSL. Format:
#
#   ALLOW <service:resource:action>[, ...] [WHERE <conditions>];
#
# Multiple ALLOW / DENY statements can be combined in one query, separated
# by semicolons. WHERE clauses support `=`, `IN (...)`, and boolean
# combinations on predicates like `settings:schemaId`, `settings:schemaGroup`,
# `settings:scope`.
#
# Verb conventions (verified against existing policies in a real Dynatrace
# account via the diagnostic script at scripts/iam-list.sh — see the
# README's "Discovering valid permission tokens" section):
#
#   - For `settings:objects`: :read, :write, :admin
#     There is NO `settings:objects:delete` token. `:admin` is the umbrella
#     verb covering full management including delete.
#
#   - For `document:documents`: :read, :write, :delete, :admin
#     Documents (dashboards, notebooks, segments in Gen 3) are a separate
#     namespace from Settings 2.0.
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

# Documents in Dynatrace Gen 3 (dashboards, notebooks, segments) live in
# the `document:documents:*` namespace — not in Settings 2.0. This grants
# full edit (read/write/delete) on all documents in the account.
# For narrower scope (e.g. only dashboards owned by a specific group),
# use a boundary on document-level attributes.
resource "dynatrace_iam_policy" "dashboard_edit" {
  name        = "dashboard-edit"
  description = "Edit documents (dashboards, notebooks, segments) — full CRUD"
  account     = var.account_uuid

  statement_query = "ALLOW document:documents:read, document:documents:write, document:documents:delete;"
}

# `settings:objects:admin` is the canonical "full admin" verb for
# Settings 2.0 — it includes implicit delete (which is not exposed as a
# standalone token). Scope-limited via the production-only boundary in
# bindings.tf.
resource "dynatrace_iam_policy" "production_admin" {
  name        = "production-admin"
  description = "Full settings admin via :admin — scope-limited via the production-only boundary"
  account     = var.account_uuid

  statement_query = "ALLOW settings:objects:admin, settings:schemas:read;"
}
