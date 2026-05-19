#!/usr/bin/env bash
#
# iam-list.sh — Dump existing Dynatrace IAM groups, policies, and
# boundaries from an account, so you can:
#
#   1. See what's already in the account before adding more
#   2. Use existing `statementQuery` strings as a Rosetta Stone for
#      the canonical permission DSL (which verbs/tokens are valid)
#   3. Identify candidates for `terraform import`
#
# Output: writes JSON files to a directory (default /tmp), one per
# resource type. Also prints a summary of unique permission tokens
# found across all policies — useful when the IAM permission catalog
# isn't well documented elsewhere.
#
# Required env vars (export in shell OR set in $REPO_ROOT/.env — the script
# auto-sources .env at startup if it exists):
#   DT_CLIENT_ID      OAuth client ID
#   DT_CLIENT_SECRET  OAuth client secret
#   DT_ACCOUNT_ID     Account UUID (8-4-4-4-12 hex)
#
# OAuth client must have scopes: account-idm-read, iam-policies-management,
# account-env-read.
#
# Usage:
#   scripts/iam-list.sh                  # writes to /tmp/iam-*.json
#   scripts/iam-list.sh -o ./out         # writes to ./out/iam-*.json
#   scripts/iam-list.sh --help

set -euo pipefail

OUT="/tmp"

usage() {
  cat <<EOF
Usage: $(basename "$0") [-o OUTPUT_DIR]

Options:
  -o, --output DIR   Directory to write JSON files to (default: /tmp)
  -h, --help         Show this help

Required env vars: DT_CLIENT_ID, DT_CLIENT_SECRET, DT_ACCOUNT_ID
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -o|--output) OUT="$2"; shift 2 ;;
    -h|--help)   usage; exit 0 ;;
    *)           echo "Unknown arg: $1"; usage; exit 2 ;;
  esac
done

# Auto-source .env at the repo root if it exists — the project's standard
# credential location (config/.env.example is its template). `set -a` exports
# every assignment so the values are visible to subshells and curl. Skipped
# silently if no .env file.
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -n "$REPO_ROOT" ] && [ -f "$REPO_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
  echo "Sourced env vars from $REPO_ROOT/.env"
fi

: "${DT_CLIENT_ID:?DT_CLIENT_ID must be set (export in shell or add to .env)}"
: "${DT_CLIENT_SECRET:?DT_CLIENT_SECRET must be set (export in shell or add to .env)}"
: "${DT_ACCOUNT_ID:?DT_ACCOUNT_ID must be set (export in shell or add to .env)}"

command -v jq >/dev/null || { echo "ERROR: jq is required"; exit 1; }
command -v curl >/dev/null || { echo "ERROR: curl is required"; exit 1; }

mkdir -p "$OUT"

TOKEN_URL="https://sso.dynatrace.com/sso/oauth2/token"
API_BASE="https://api.dynatrace.com"

echo "[1/5] Exchanging OAuth client credentials for a bearer token..."
TOKEN_RESPONSE=$(curl -sS -X POST "$TOKEN_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=client_credentials" \
  --data-urlencode "client_id=$DT_CLIENT_ID" \
  --data-urlencode "client_secret=$DT_CLIENT_SECRET" \
  --data-urlencode "scope=account-idm-read iam-policies-management account-env-read" \
  --data-urlencode "resource=urn:dtaccount:$DT_ACCOUNT_ID")

TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token // empty')
if [ -z "$TOKEN" ]; then
  echo "ERROR: token exchange failed. Response:"
  echo "$TOKEN_RESPONSE" | jq . 2>/dev/null || echo "$TOKEN_RESPONSE"
  exit 1
fi
echo "      OK (${#TOKEN} chars)"

H="Authorization: Bearer $TOKEN"

echo "[2/5] GET groups → $OUT/iam-groups.json"
curl -sS "$API_BASE/iam/v1/accounts/$DT_ACCOUNT_ID/groups" -H "$H" > "$OUT/iam-groups.json"

echo "[3/5] GET policy summaries → $OUT/iam-policies-list.json"
curl -sS "$API_BASE/iam/v1/repo/account/$DT_ACCOUNT_ID/policies" -H "$H" > "$OUT/iam-policies-list.json"

echo "[4/5] GET full policy details (one fetch per UUID) → $OUT/iam-policies-detail.json"
UUIDS=$(jq -r '.policies[]?.uuid // .items[]?.uuid // empty' "$OUT/iam-policies-list.json")
echo "[]" > "$OUT/iam-policies-detail.json"
for uuid in $UUIDS; do
  DETAIL=$(curl -sS "$API_BASE/iam/v1/repo/account/$DT_ACCOUNT_ID/policies/$uuid" -H "$H")
  jq --argjson d "$DETAIL" '. += [$d]' "$OUT/iam-policies-detail.json" > "$OUT/iam-policies-detail.json.tmp"
  mv "$OUT/iam-policies-detail.json.tmp" "$OUT/iam-policies-detail.json"
done
COUNT=$(jq 'length' "$OUT/iam-policies-detail.json")
echo "      Fetched $COUNT policy details"

echo "[5/5] GET boundaries → $OUT/iam-boundaries.json"
curl -sS "$API_BASE/iam/v1/repo/account/$DT_ACCOUNT_ID/boundaries" -H "$H" > "$OUT/iam-boundaries.json"

echo
echo "=== Files written ==="
ls -la "$OUT"/iam-*.json

echo
echo "=== Unique permission tokens used across all policies ==="
echo "(this is your account's canonical IAM DSL vocabulary)"
jq -r '.[].statementQuery // empty' "$OUT/iam-policies-detail.json" \
  | grep -oE '[a-z][a-z0-9-]*:[a-z][a-z0-9-]*:[a-z][a-z0-9_-]*' \
  | sort -u \
  | sed 's/^/  /'
