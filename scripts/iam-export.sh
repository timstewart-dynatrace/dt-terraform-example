#!/usr/bin/env bash
#
# iam-export.sh — Bulk export existing Dynatrace IAM resources to HCL files.
#
# Uses the `dynatrace-oss/dynatrace` provider's built-in export utility,
# which runs the provider binary directly with the `-export` flag. IAM
# resources are excluded from export by default (reason from the
# provider's -list-exclusions: "Account management requires OAuth2
# client and is specific to SaaS"), so they must be named explicitly.
#
# Required env vars (export in shell OR set in $REPO_ROOT/.env — the script
# auto-sources .env at startup if it exists):
#   DT_CLIENT_ID       OAuth client ID
#   DT_CLIENT_SECRET   OAuth client secret
#   DT_ACCOUNT_ID      Account UUID (8-4-4-4-12 hex)
#   DYNATRACE_ENV_URL  Any valid Dynatrace tenant URL — required by the
#                      export utility at provider startup even for IAM-only
#                      runs (the URL isn't actually used for IAM API calls).
#                      Fallback chain (highest to lowest):
#                        1. DYNATRACE_ENV_URL already exported
#                        2. Derived from `environment_id` in
#                           terraform/iam/terraform.tfvars as
#                           https://<environment_id>.live.dynatrace.com
#                        3. SOURCE_TENANT_URL from migration pipeline config
#                        4. TARGET_TENANT_URL from migration pipeline config
#                      (For Gen 3 tenants on .apps.dynatrace.com, set
#                      DYNATRACE_ENV_URL explicitly — the tfvars derivation
#                      assumes .live.)
#
# OAuth client scopes needed: account-idm-read, iam-policies-management,
# account-env-read.
#
# Prerequisite: `terraform init` must have been run in terraform/iam/
# so the provider binary is downloaded to .terraform/providers/.
#
# Usage:
#   scripts/iam-export.sh                              # default 4 IAM resource types
#   scripts/iam-export.sh dynatrace_iam_user           # add extras
#   scripts/iam-export.sh -o /tmp/iam-out              # custom output dir
#   scripts/iam-export.sh --help

set -euo pipefail

# Default resource types to export. Extras can be appended via positional args.
DEFAULT_RESOURCES=(
  dynatrace_iam_group
  dynatrace_iam_policy
  dynatrace_iam_policy_boundary
  dynatrace_iam_policy_bindings_v2
)

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "ERROR: must be run inside a git repository"
  exit 1
}
OUT_DIR="$REPO_ROOT/exported-iam"

usage() {
  cat <<EOF
Usage: $(basename "$0") [-o OUTPUT_DIR] [extra_resource_type ...]

Options:
  -o, --output DIR   Directory to write HCL files to (default: $REPO_ROOT/exported-iam)
  -h, --help         Show this help

Examples:
  $(basename "$0")
  $(basename "$0") dynatrace_iam_user
  $(basename "$0") -o /tmp/iam-out dynatrace_iam_user dynatrace_iam_service_user
EOF
}

EXTRA_RESOURCES=()
while [ $# -gt 0 ]; do
  case "$1" in
    -o|--output) OUT_DIR="$2"; shift 2 ;;
    -h|--help)   usage; exit 0 ;;
    -*)          echo "Unknown flag: $1"; usage; exit 2 ;;
    *)           EXTRA_RESOURCES+=("$1"); shift ;;
  esac
done

# Auto-source .env at the repo root if it exists — the project's standard
# credential location (config/.env.example is its template). `set -a` exports
# every assignment so the values are visible to child processes (the provider
# binary). Skipped silently if no .env file.
if [ -f "$REPO_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
  echo "Sourced env vars from $REPO_ROOT/.env"
fi

: "${DT_CLIENT_ID:?DT_CLIENT_ID must be set (export in shell or add to .env)}"
: "${DT_CLIENT_SECRET:?DT_CLIENT_SECRET must be set (export in shell or add to .env)}"
: "${DT_ACCOUNT_ID:?DT_ACCOUNT_ID must be set (export in shell or add to .env)}"

# The export utility requires DYNATRACE_ENV_URL at provider startup even for
# IAM-only exports (account-level, no tenant in the API path — the URL isn't
# actually used for IAM API calls). Fallback chain, in priority order:
#   1. DYNATRACE_ENV_URL already exported
#   2. Derived from `environment_id` in terraform/iam/terraform.tfvars
#      (the canonical source for the IAM Terraform config)
#   3. SOURCE_TENANT_URL or TARGET_TENANT_URL from the migration pipeline
#      config
if [ -z "${DYNATRACE_ENV_URL:-}" ]; then
  TFVARS="$REPO_ROOT/terraform/iam/terraform.tfvars"
  TFVARS_ENV_ID=""
  if [ -f "$TFVARS" ]; then
    # Match: environment_id = "yhu28601"  (with optional whitespace).
    # Extract the quoted value.
    TFVARS_ENV_ID=$(sed -nE 's/^[[:space:]]*environment_id[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$TFVARS" | head -1)
  fi

  if [ -n "$TFVARS_ENV_ID" ]; then
    export DYNATRACE_ENV_URL="https://${TFVARS_ENV_ID}.live.dynatrace.com"
    echo "Derived DYNATRACE_ENV_URL from terraform/iam/terraform.tfvars: $DYNATRACE_ENV_URL"
  elif [ -n "${SOURCE_TENANT_URL:-}" ]; then
    export DYNATRACE_ENV_URL="$SOURCE_TENANT_URL"
    echo "Using SOURCE_TENANT_URL as DYNATRACE_ENV_URL: $DYNATRACE_ENV_URL"
  elif [ -n "${TARGET_TENANT_URL:-}" ]; then
    export DYNATRACE_ENV_URL="$TARGET_TENANT_URL"
    echo "Using TARGET_TENANT_URL as DYNATRACE_ENV_URL: $DYNATRACE_ENV_URL"
  else
    echo "ERROR: no tenant URL found."
    echo "       Tried (in order):"
    echo "         1. \$DYNATRACE_ENV_URL"
    echo "         2. environment_id in $TFVARS"
    echo "         3. \$SOURCE_TENANT_URL"
    echo "         4. \$TARGET_TENANT_URL"
    echo "       Set one of them, or export DYNATRACE_ENV_URL directly."
    exit 1
  fi
fi

# Locate the provider binary. `terraform init` puts it under
# .terraform/providers/registry.terraform.io/dynatrace-oss/dynatrace/<version>/<os_arch>/.
PROVIDER_DIR="$REPO_ROOT/terraform/iam/.terraform/providers/registry.terraform.io/dynatrace-oss/dynatrace"
if [ ! -d "$PROVIDER_DIR" ]; then
  echo "ERROR: provider not initialized. Run this first:"
  echo "  cd $REPO_ROOT/terraform/iam && terraform init"
  exit 1
fi

BINARY=$(find "$PROVIDER_DIR" -name "terraform-provider-dynatrace_v*" -type f 2>/dev/null | head -1)
if [ -z "$BINARY" ]; then
  echo "ERROR: provider binary not found under $PROVIDER_DIR"
  echo "Try: cd $REPO_ROOT/terraform/iam && terraform init -upgrade"
  exit 1
fi

RESOURCES=("${DEFAULT_RESOURCES[@]}")
# bash 3.2 (macOS default) treats empty array expansion as "unbound variable"
# under `set -u`, even when the array was explicitly declared. Only append
# extras when there's at least one.
if [ ${#EXTRA_RESOURCES[@]} -gt 0 ]; then
  RESOURCES+=("${EXTRA_RESOURCES[@]}")
fi

mkdir -p "$OUT_DIR"

echo "Provider binary: $BINARY"
echo "Output dir:      $OUT_DIR"
echo "Resources:       ${RESOURCES[*]}"
echo

# The export utility writes to ./.configuration relative to CWD by default,
# or to DYNATRACE_TARGET_FOLDER if set. -flat = no module structure,
# -id = include source IDs as comments in generated HCL.
export DYNATRACE_TARGET_FOLDER="$OUT_DIR"
(cd "$OUT_DIR" && "$BINARY" -export -flat -id "${RESOURCES[@]}")

echo
echo "=== Summary ==="
TF_COUNT=$(find "$OUT_DIR" -type f -name "*.tf" 2>/dev/null | wc -l | tr -d ' ')
echo "  $TF_COUNT .tf files written under $OUT_DIR"
echo
echo "Next steps:"
echo "  1. cd $OUT_DIR && ls"
echo "  2. Review generated HCL — strip resources you don't want managed"
echo "  3. terraform fmt and terraform validate (after providing a versions.tf + providers.tf)"
echo "  4. terraform import <addr> <id>   # for each resource you want under Terraform mgmt"
