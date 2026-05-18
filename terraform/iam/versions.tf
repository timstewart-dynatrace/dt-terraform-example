terraform {
  required_version = ">= 1.5"

  required_providers {
    dynatrace = {
      source = "dynatrace-oss/dynatrace"
      # Pinned to the 1.96 line — current at the time this scaffold was written
      # (v1.96.0 published 2026-05-06). Bump after verifying IAM resource args
      # against the new release notes; argument names have shifted in past
      # provider releases.
      version = "~> 1.96"
    }
  }
}
