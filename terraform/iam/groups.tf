# IAM groups. Names should match the SSO/IdP group claims if you are
# federating identity (Azure AD, Okta, etc.) — Dynatrace matches incoming
# claim values to group names.
#
# Note: the deprecated `permissions` block is intentionally omitted.
# Use policy bindings (see bindings.tf) for permission assignment.

resource "dynatrace_iam_group" "platform_team" {
  name        = "platform-team"
  description = "Platform engineering — full admin access, scoped to production via boundary"
}

resource "dynatrace_iam_group" "dashboard_readers" {
  name        = "dashboard-readers"
  description = "Read-only access to monitoring data + dashboard editing"
}
