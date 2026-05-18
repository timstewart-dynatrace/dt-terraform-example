# Permission boundaries restrict policies at binding time. The boundary's
# `query` is a condition that gets AND-ed onto the policy's statement_query
# when the policy is bound to a group via this boundary.
#
# Common boundary patterns:
#   environment:management-zone = "<mz-id>"
#   environment:management-zone startsWith "[Prod]"
#   environment:host-tag = "production"

resource "dynatrace_iam_policy_boundary" "production_only" {
  name  = "production-only"
  query = "environment:management-zone = \"${var.management_zone_id}\";"
}
