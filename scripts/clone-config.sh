#!/bin/bash
#
# Clone configuration from a Dynatrace source tenant
# Downloads configuration using the Dynatrace API into a timestamped directory
#
# Usage:
#   ./clone-config.sh <source-url> <source-token> [config-types]
#

set -o errexit
set -o nounset
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Validate arguments
if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <source-url> <source-token> [config-types]"
    echo ""
    echo "Examples:"
    echo "  $0 https://tenant.live.dynatrace.com token_xyz"
    echo "  $0 https://tenant.live.dynatrace.com token_xyz dashboard,management-zone"
    exit 1
fi

SOURCE_URL="${1%/}"  # Remove trailing slash
SOURCE_TOKEN="$2"
CONFIG_TYPES="${3:-}"

OUTPUT_DIR="config/cloned-$(date +%Y%m%d-%H%M%S)"

log_info "Cloning configuration from $SOURCE_URL"
log_info "Output directory: $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"

# Determine which types to download
if [[ -n "$CONFIG_TYPES" ]]; then
    TYPES=$(echo "$CONFIG_TYPES" | tr ',' ' ')
else
    TYPES="alerting-profiles auto-tag dashboard extension management-zone notification request-naming synthetic-location synthetic-monitor"
fi

TOTAL_ITEMS=0

for config_type in $TYPES; do
    ENDPOINT=""
    LIST_KEY=""
    DETAIL_ENDPOINT=""

    case "$config_type" in
        alerting-profiles) ENDPOINT="/api/config/v1/alertingProfiles"; LIST_KEY="values"; DETAIL_ENDPOINT="/api/config/v1/alertingProfiles" ;;
        auto-tag) ENDPOINT="/api/config/v1/autoTags"; LIST_KEY="values"; DETAIL_ENDPOINT="/api/config/v1/autoTags" ;;
        dashboard) ENDPOINT="/api/config/v1/dashboards"; LIST_KEY="dashboards"; DETAIL_ENDPOINT="/api/config/v1/dashboards" ;;
        management-zone) ENDPOINT="/api/config/v1/managementZones"; LIST_KEY="values"; DETAIL_ENDPOINT="/api/config/v1/managementZones" ;;
        notification) ENDPOINT="/api/config/v1/notifications"; LIST_KEY="values"; DETAIL_ENDPOINT="/api/config/v1/notifications" ;;
        request-naming) ENDPOINT="/api/config/v1/service/requestNaming"; LIST_KEY="values"; DETAIL_ENDPOINT="/api/config/v1/service/requestNaming" ;;
        extension) ENDPOINT="/api/config/v1/extensions"; LIST_KEY="extensions"; DETAIL_ENDPOINT="/api/config/v1/extensions" ;;
        synthetic-monitor) ENDPOINT="/api/v1/synthetic/monitors"; LIST_KEY="monitors"; DETAIL_ENDPOINT="/api/v1/synthetic/monitors" ;;
        synthetic-location) ENDPOINT="/api/v1/synthetic/locations"; LIST_KEY="locations"; DETAIL_ENDPOINT="" ;;
        *)
            log_info "Skipping unknown config type: $config_type"
            continue
            ;;
    esac

    RESPONSE=$(curl -s -H "Authorization: Api-Token $SOURCE_TOKEN" "$SOURCE_URL$ENDPOINT" 2>&1 || true)

    if ! command -v jq &> /dev/null; then
        mkdir -p "$OUTPUT_DIR/$config_type"
        echo "$RESPONSE" > "$OUTPUT_DIR/$config_type/_all.json"
        TOTAL_ITEMS=$((TOTAL_ITEMS + 1))
        continue
    fi

    ITEM_COUNT=$(echo "$RESPONSE" | jq -r ".$LIST_KEY | length" 2>/dev/null || echo "0")
    if [[ "$ITEM_COUNT" == "0" || "$ITEM_COUNT" == "null" ]]; then
        continue
    fi

    mkdir -p "$OUTPUT_DIR/$config_type"

    if [[ -z "$DETAIL_ENDPOINT" ]]; then
        echo "$RESPONSE" | jq ".$LIST_KEY" > "$OUTPUT_DIR/$config_type/_all.json"
        TOTAL_ITEMS=$((TOTAL_ITEMS + ITEM_COUNT))
    else
        IDS=$(echo "$RESPONSE" | jq -r ".$LIST_KEY[]? | .id // .entityId // empty" 2>/dev/null || true)
        for ITEM_ID in $IDS; do
            ITEM_RESPONSE=$(curl -s -H "Authorization: Api-Token $SOURCE_TOKEN" "$SOURCE_URL$DETAIL_ENDPOINT/$ITEM_ID" 2>&1 || true)
            SAFE_NAME=$(echo "$ITEM_ID" | tr -c '[:alnum:]-_' '_' | head -c 80)
            echo "$ITEM_RESPONSE" | jq '.' > "$OUTPUT_DIR/$config_type/${SAFE_NAME}.json" 2>/dev/null || \
                echo "$ITEM_RESPONSE" > "$OUTPUT_DIR/$config_type/${SAFE_NAME}.json"
            TOTAL_ITEMS=$((TOTAL_ITEMS + 1))
        done
    fi

    log_info "  Downloaded $ITEM_COUNT $config_type item(s)"
done

log_success "Configuration cloned: $TOTAL_ITEMS total items"
log_info "Location: $(pwd)/$OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "1. Review the configuration: ls -la $OUTPUT_DIR"
echo "2. Customize as needed"
echo "3. Set up Terraform provider and deploy to target tenant"
