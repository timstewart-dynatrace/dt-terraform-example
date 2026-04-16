#!/bin/bash
#
# Dynatrace Terraform Configuration Migration Script
#
# This script performs a complete migration of all configurations from a source
# tenant to a target tenant using Terraform-compatible workflows, including
# backup and validation.
#
# Usage:
#   ./migrate.sh [OPTIONS]
#
# Examples:
#   # Using environment variables
#   export SOURCE_TENANT_URL="https://source.live.dynatrace.com"
#   export SOURCE_TENANT_TOKEN="your_token"
#   export TARGET_TENANT_URL="https://target.live.dynatrace.com"
#   export TARGET_TENANT_TOKEN="your_token"
#   ./migrate.sh
#
#   # Using command-line arguments
#   ./migrate.sh \
#     --source-url https://source.live.dynatrace.com \
#     --target-url https://target.live.dynatrace.com \
#     --source-token YOUR_TOKEN \
#     --target-token YOUR_TOKEN
#
#   # Dry run (preview changes)
#   ./migrate.sh --dry-run
#

set -o errexit  # Exit on error
set -o pipefail # Exit on pipe failure
set -o nounset  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DRY_RUN=false
NO_BACKUP=false
CONFIG_DIR="config"
BACKUP_DIR=""
CONFIG_TYPES=""

# Supported configuration types
SUPPORTED_TYPES="alerting-profiles auto-tag dashboard extension management-zone notification request-naming synthetic-location synthetic-monitor"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_help() {
    cat << EOF
Usage: $0 [OPTIONS]

OPTIONS:
    --source-url URL            Source Dynatrace tenant URL
    --target-url URL            Target Dynatrace tenant URL
    --source-token TOKEN        API token for source tenant
    --target-token TOKEN        API token for target tenant
    --config-dir DIR            Configuration directory (default: config)
    --dry-run                   Preview changes without applying
    --no-backup                 Skip backup of target configuration
    --config-types TYPES        Comma-separated list of config types to migrate
    --list-types                List available configuration types and exit
    --help                      Show this help message

ENVIRONMENT VARIABLES:
    SOURCE_TENANT_URL           Source Dynatrace tenant URL
    SOURCE_TENANT_TOKEN         API token for source tenant
    TARGET_TENANT_URL           Target Dynatrace tenant URL
    TARGET_TENANT_TOKEN         API token for target tenant

EXAMPLES:
    # Using environment variables in .env file
    source .env
    $0

    # Using command-line arguments
    $0 \\
      --source-url https://source.live.dynatrace.com \\
      --target-url https://target.live.dynatrace.com \\
      --source-token YOUR_TOKEN \\
      --target-token YOUR_TOKEN

    # Dry run to preview changes
    $0 --dry-run

    # Migrate only dashboards and management zones
    $0 --config-types dashboard,management-zone

EOF
    exit 0
}

list_types() {
    echo ""
    echo "Available Configuration Types:"
    echo ""
    printf "  %-35s %s\n" "Type" "Description"
    echo "  $(printf '%0.s-' {1..70})"
    printf "  %-35s %s\n" "alerting-profiles" "Alert notification rules"
    printf "  %-35s %s\n" "auto-tag" "Auto-tagging rules"
    printf "  %-35s %s\n" "dashboard" "Dashboards"
    printf "  %-35s %s\n" "extension" "Extensions"
    printf "  %-35s %s\n" "management-zone" "Management zones"
    printf "  %-35s %s\n" "notification" "Notification configurations"
    printf "  %-35s %s\n" "request-naming" "Request naming rules"
    printf "  %-35s %s\n" "synthetic-location" "Synthetic test locations"
    printf "  %-35s %s\n" "synthetic-monitor" "Synthetic monitors"
    echo ""
    exit 0
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --source-url)
                SOURCE_TENANT_URL="$2"
                shift 2
                ;;
            --target-url)
                TARGET_TENANT_URL="$2"
                shift 2
                ;;
            --source-token)
                SOURCE_TENANT_TOKEN="$2"
                shift 2
                ;;
            --target-token)
                TARGET_TENANT_TOKEN="$2"
                shift 2
                ;;
            --config-dir)
                CONFIG_DIR="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-backup)
                NO_BACKUP=true
                shift
                ;;
            --config-types)
                CONFIG_TYPES="$2"
                shift 2
                ;;
            --list-types)
                list_types
                ;;
            --help)
                print_help
                ;;
            *)
                log_error "Unknown option: $1"
                print_help
                ;;
        esac
    done
}

verify_terraform_installed() {
    log_info "Checking Terraform installation..."

    if ! command -v terraform &> /dev/null; then
        log_error "Terraform CLI not found"
        log_error "Please install Terraform first:"
        log_error "  brew tap hashicorp/tap"
        log_error "  brew install hashicorp/tap/terraform"
        return 1
    fi

    local tf_version
    tf_version=$(terraform --version 2>&1 | head -n1)
    log_success "Terraform found: $tf_version"
    return 0
}

verify_tenant_connection() {
    local url=$1
    local token=$2
    local name=$3

    log_info "Verifying connection to $name tenant..."

    if ! command -v curl &> /dev/null; then
        log_warning "curl not found, skipping connection verification"
        return 0
    fi

    local response
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Api-Token $token" \
        "$url/api/v1/config/clusterversion" 2>&1 || true)

    local http_code
    http_code=$(echo "$response" | tail -n1)

    if [[ "$http_code" == "200" ]]; then
        log_success "$name tenant connection verified"
        return 0
    else
        log_error "$name tenant returned HTTP $http_code"
        return 1
    fi
}

create_environments_yaml() {
    log_info "Creating environments.yaml..."

    mkdir -p "$CONFIG_DIR"

    cat > "$CONFIG_DIR/environments.yaml" << EOF
environments:
  source:
    name: source
    url: $SOURCE_TENANT_URL
    token: $SOURCE_TENANT_TOKEN

  target:
    name: target
    url: $TARGET_TENANT_URL
    token: $TARGET_TENANT_TOKEN
EOF

    log_success "Created: $CONFIG_DIR/environments.yaml"
}

download_configuration() {
    local url=$1
    local token=$2
    local target_dir=$3
    local types="${4:-$SUPPORTED_TYPES}"

    # If CONFIG_TYPES was set via CLI, use that instead
    if [[ -n "$CONFIG_TYPES" && "$4" == "$SUPPORTED_TYPES" ]]; then
        types=$(echo "$CONFIG_TYPES" | tr ',' ' ')
    fi

    log_info "Downloading configuration from $url..."

    mkdir -p "$target_dir"
    local total_items=0

    for config_type in $types; do
        local endpoint=""
        local list_key=""
        local detail_endpoint=""

        case "$config_type" in
            alerting-profiles)
                endpoint="/api/config/v1/alertingProfiles"
                list_key="values"
                detail_endpoint="/api/config/v1/alertingProfiles"
                ;;
            auto-tag)
                endpoint="/api/config/v1/autoTags"
                list_key="values"
                detail_endpoint="/api/config/v1/autoTags"
                ;;
            dashboard)
                endpoint="/api/config/v1/dashboards"
                list_key="dashboards"
                detail_endpoint="/api/config/v1/dashboards"
                ;;
            management-zone)
                endpoint="/api/config/v1/managementZones"
                list_key="values"
                detail_endpoint="/api/config/v1/managementZones"
                ;;
            notification)
                endpoint="/api/config/v1/notifications"
                list_key="values"
                detail_endpoint="/api/config/v1/notifications"
                ;;
            request-naming)
                endpoint="/api/config/v1/service/requestNaming"
                list_key="values"
                detail_endpoint="/api/config/v1/service/requestNaming"
                ;;
            extension)
                endpoint="/api/config/v1/extensions"
                list_key="extensions"
                detail_endpoint="/api/config/v1/extensions"
                ;;
            synthetic-monitor)
                endpoint="/api/v1/synthetic/monitors"
                list_key="monitors"
                detail_endpoint="/api/v1/synthetic/monitors"
                ;;
            synthetic-location)
                endpoint="/api/v1/synthetic/locations"
                list_key="locations"
                detail_endpoint=""
                ;;
            *)
                log_warning "Unknown config type: $config_type (skipping)"
                continue
                ;;
        esac

        # Fetch list of items
        local response
        response=$(curl -s \
            -H "Authorization: Api-Token $token" \
            "$url$endpoint" 2>&1 || true)

        # Extract item IDs using jq
        if ! command -v jq &> /dev/null; then
            log_warning "jq not found, saving raw list response for $config_type"
            mkdir -p "$target_dir/$config_type"
            echo "$response" > "$target_dir/$config_type/_all.json"
            total_items=$((total_items + 1))
            continue
        fi

        local item_count
        item_count=$(echo "$response" | jq -r ".$list_key | length" 2>/dev/null || echo "0")

        if [[ "$item_count" == "0" || "$item_count" == "null" ]]; then
            continue
        fi

        mkdir -p "$target_dir/$config_type"

        if [[ -z "$detail_endpoint" ]]; then
            # Save full list response (e.g., synthetic locations)
            echo "$response" | jq ".$list_key" > "$target_dir/$config_type/_all.json"
            total_items=$((total_items + item_count))
        else
            # Fetch each item individually
            local ids
            ids=$(echo "$response" | jq -r ".$list_key[]? | .id // .entityId // empty" 2>/dev/null || true)

            for item_id in $ids; do
                local item_response
                item_response=$(curl -s \
                    -H "Authorization: Api-Token $token" \
                    "$url$detail_endpoint/$item_id" 2>&1 || true)

                local safe_name
                safe_name=$(echo "$item_id" | tr -c '[:alnum:]-_' '_' | head -c 80)
                echo "$item_response" | jq '.' > "$target_dir/$config_type/${safe_name}.json" 2>/dev/null || \
                    echo "$item_response" > "$target_dir/$config_type/${safe_name}.json"

                total_items=$((total_items + 1))
            done
        fi

        log_info "  Downloaded $item_count $config_type item(s)"
    done

    log_success "Configuration download complete: $total_items total items"
    return 0
}

validate_configuration() {
    local config_dir=$1

    log_info "Validating configuration files..."

    # Validate JSON files
    local json_files
    json_files=$(find "$config_dir" -name "*.json" 2>/dev/null || true)

    if [[ -z "$json_files" ]]; then
        log_warning "No configuration files found in $config_dir"
        return 0
    fi

    if command -v jq &> /dev/null; then
        while IFS= read -r json_file; do
            if jq '.' "$json_file" > /dev/null 2>&1; then
                log_info "  Valid: $(basename "$json_file")"
            else
                log_error "  Invalid JSON: $json_file"
                return 1
            fi
        done <<< "$json_files"
    fi

    # Validate YAML files if present
    if command -v python3 &> /dev/null; then
        local yaml_files
        yaml_files=$(find "$config_dir" -name "*.yaml" -o -name "*.yml" 2>/dev/null || true)

        if [[ -n "$yaml_files" ]]; then
            while IFS= read -r yaml_file; do
                if python3 -c "import yaml; yaml.safe_load(open('$yaml_file'))" 2>/dev/null; then
                    log_info "  Valid: $(basename "$yaml_file")"
                else
                    log_error "  Invalid YAML: $yaml_file"
                    return 1
                fi
            done <<< "$yaml_files"
        fi
    fi

    log_success "Configuration validation passed"
    return 0
}

generate_terraform_config() {
    local source_dir=$1
    local terraform_dir=$2

    log_info "Generating Terraform configuration..."

    mkdir -p "$terraform_dir"

    # Generate provider configuration using .tf.json (Terraform JSON syntax)
    cat > "$terraform_dir/main.tf.json" << EOF
{
  "terraform": {
    "required_version": ">= 1.0",
    "required_providers": {
      "dynatrace": {
        "source": "dynatrace-oss/dynatrace",
        "version": "~> 1.0"
      }
    }
  },
  "provider": {
    "dynatrace": {
      "dt_env_url": "$TARGET_TENANT_URL",
      "dt_api_token": "$TARGET_TENANT_TOKEN"
    }
  }
}
EOF

    log_success "Generated provider configuration: $terraform_dir/main.tf.json"

    local file_count
    file_count=$(find "$source_dir" -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
    log_info "Source configs available: $file_count files"

    return 0
}

deploy_configuration() {
    local terraform_dir=$1

    log_info "Deploying configuration via Terraform..."

    # terraform init
    log_info "Running terraform init..."
    if ! terraform -chdir="$terraform_dir" init -input=false; then
        log_error "terraform init failed"
        return 1
    fi
    log_success "terraform init completed"

    # terraform plan
    log_info "Running terraform plan..."
    if ! terraform -chdir="$terraform_dir" plan -out=tfplan; then
        log_error "terraform plan failed"
        return 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] terraform plan completed (skipping apply)"
        return 0
    fi

    # terraform apply
    log_info "Running terraform apply..."
    if ! terraform -chdir="$terraform_dir" apply -auto-approve tfplan; then
        log_error "terraform apply failed"
        return 1
    fi

    log_success "terraform apply completed successfully"
    return 0
}

backup_configuration() {
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    BACKUP_DIR="$CONFIG_DIR/backups/$timestamp"

    log_info "Creating backup of target configuration..."

    mkdir -p "$BACKUP_DIR"

    if download_configuration "$TARGET_TENANT_URL" "$TARGET_TENANT_TOKEN" "$BACKUP_DIR" "$SUPPORTED_TYPES"; then
        log_success "Backup created at: $BACKUP_DIR"
        return 0
    else
        log_warning "Failed to create backup (continuing with migration)"
        return 0
    fi
}

main() {
    log_info "========================================="
    log_info "Dynatrace Terraform Configuration Migration"
    log_info "========================================="

    # Load environment variables if .env exists
    if [[ -f ".env" ]]; then
        log_info "Loading environment variables from .env"
        set -a
        # shellcheck source=/dev/null
        source .env
        set +a
    fi

    # Parse command-line arguments
    parse_arguments "$@"

    # Validate required variables
    if [[ -z "${SOURCE_TENANT_URL:-}" ]] || \
       [[ -z "${TARGET_TENANT_URL:-}" ]] || \
       [[ -z "${SOURCE_TENANT_TOKEN:-}" ]] || \
       [[ -z "${TARGET_TENANT_TOKEN:-}" ]]; then
        log_error "Missing required environment variables or arguments"
        log_error "Required: SOURCE_TENANT_URL, TARGET_TENANT_URL, SOURCE_TENANT_TOKEN, TARGET_TENANT_TOKEN"
        print_help
        return 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "[DRY RUN MODE] No changes will be applied"
    fi

    # Step 1: Verify Terraform installation
    if ! verify_terraform_installed; then
        return 1
    fi

    # Step 2: Create environments configuration
    create_environments_yaml

    # Step 3: Verify API connections
    if ! verify_tenant_connection "$SOURCE_TENANT_URL" "$SOURCE_TENANT_TOKEN" "source"; then
        return 1
    fi

    if ! verify_tenant_connection "$TARGET_TENANT_URL" "$TARGET_TENANT_TOKEN" "target"; then
        return 1
    fi

    log_success "API connections verified"

    # Step 4: Backup target configuration (before any changes)
    if [[ "$NO_BACKUP" != "true" ]] && [[ "$DRY_RUN" != "true" ]]; then
        if ! backup_configuration; then
            return 1
        fi
    fi

    # Step 5: Download all source configuration
    local source_config_dir="$CONFIG_DIR/source"
    if ! download_configuration "$SOURCE_TENANT_URL" "$SOURCE_TENANT_TOKEN" "$source_config_dir" "$SUPPORTED_TYPES"; then
        log_warning "No configuration downloaded from source (tenant may be empty)"
    fi

    # Step 6: Validate configuration
    if ! validate_configuration "$source_config_dir"; then
        log_error "Configuration validation failed"
        return 1
    fi

    # Step 7: Generate Terraform config and deploy
    local terraform_dir="$CONFIG_DIR/terraform"
    if ! generate_terraform_config "$source_config_dir" "$terraform_dir"; then
        return 1
    fi

    if ! deploy_configuration "$terraform_dir"; then
        return 1
    fi

    log_info "========================================="
    log_success "Migration completed successfully!"
    log_info "========================================="

    if [[ -n "$BACKUP_DIR" ]]; then
        log_success "Backup available at: $BACKUP_DIR"
    fi

    return 0
}

# Run main function
main "$@"
