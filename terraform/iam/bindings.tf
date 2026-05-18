# Bind groups to policies. One bindings_v2 resource per (group, scope) pair.
#
# IMPORTANT: bindings_v2 re-assigns ALL policies for a group within the
# given scope. Every policy that should remain bound must be listed here —
# omitting one unbinds it. Per the provider docs, there is a brief window
# during apply where the group has no policies assigned.

# platform-team → production-admin, restricted to the production management
# zone by the production-only boundary.
resource "dynatrace_iam_policy_bindings_v2" "platform_team_admin" {
  group   = dynatrace_iam_group.platform_team.id
  account = var.account_uuid

  policy {
    id         = dynatrace_iam_policy.production_admin.id
    boundaries = [dynatrace_iam_policy_boundary.production_only.id]
  }
}

# dashboard-readers → monitoring-read-only + dashboard-edit. No boundary
# (these are intentionally global to the account).
resource "dynatrace_iam_policy_bindings_v2" "dashboard_readers" {
  group   = dynatrace_iam_group.dashboard_readers.id
  account = var.account_uuid

  policy {
    id = dynatrace_iam_policy.monitoring_read_only.id
  }

  policy {
    id = dynatrace_iam_policy.dashboard_edit.id
  }
}
