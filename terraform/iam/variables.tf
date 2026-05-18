variable "account_uuid" {
  type        = string
  description = "Dynatrace account UUID — visible in the account.dynatrace.com URL. Format: 8-4-4-4-12 hex (e.g. abc12345-1234-1234-1234-abcdef012345). Do NOT include the urn:dtaccount: prefix."

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.account_uuid))
    error_message = "account_uuid must be a UUID in 8-4-4-4-12 hex format, without the urn:dtaccount: prefix."
  }
}

variable "environment_id" {
  type        = string
  description = "Dynatrace environment (tenant) ID — the subdomain portion of https://<environment-id>.live.dynatrace.com. Used to qualify management-zone-scoped permissions."
}

variable "management_zone_id" {
  type        = string
  description = "Management zone ID used by the production-only boundary example. Replace with a real MZ ID from your tenant before applying."
  default     = "REPLACE_WITH_REAL_MZ_ID"
}
