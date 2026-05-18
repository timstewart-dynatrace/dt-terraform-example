# Account-level IAM policies. Each policy is a `statement_query` in
# Dynatrace's permission DSL. Format:
#
#   ALLOW <service:resource:action>[, ...] [WHERE <conditions>];
#
# Bindings in bindings.tf attach these policies to groups. Policies and
# bindings must agree on scope — these are all account-level, so the
# corresponding bindings use `account = var.account_uuid`.

resource "dynatrace_iam_policy" "monitoring_read_only" {
  name        = "monitoring-read-only"
  description = "Read settings, dashboards, entities, and problems"
  account     = var.account_uuid

  statement_query = "ALLOW settings:objects:read, settings:schemas:read, entities:read, davis-problems:read;"
}

resource "dynatrace_iam_policy" "dashboard_edit" {
  name        = "dashboard-edit"
  description = "Create, edit, and delete dashboards (no other write access)"
  account     = var.account_uuid

  statement_query = "ALLOW document:documents:read, document:documents:write, document:documents:delete WHERE document:type = \"dashboard\";"
}

resource "dynatrace_iam_policy" "production_admin" {
  name        = "production-admin"
  description = "Full settings admin — scope-limited via the production-only boundary"
  account     = var.account_uuid

  statement_query = "ALLOW settings:objects:read, settings:objects:write, settings:objects:delete, settings:schemas:read;"
}
