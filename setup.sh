#!/bin/bash
#
# Quick Setup Script for Dynatrace Terraform Configuration Migration
#
# This script helps you set up the migration environment quickly.
# It will:
# 1. Check dependencies
# 2. Collect configuration from user
# 3. Create .env file
# 4. Verify connections
#
# Usage:
#   ./setup.sh
#

set -o errexit
set -o nounset
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
+================================================================+
|  Dynatrace Terraform Configuration Migration - Setup Wizard    |
+================================================================+
EOF
echo -e "${NC}"

# Check dependencies
echo -e "\n${BLUE}[1/4] Checking dependencies...${NC}"

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 (required)"
        return 1
    fi
}

all_deps_ok=true

check_command "python3" || all_deps_ok=false
check_command "curl" || all_deps_ok=false
check_command "jq" || all_deps_ok=false

if ! check_command "terraform"; then
    echo -e "  ${YELLOW}!${NC} Terraform not in PATH (you'll need to install it)"
    all_deps_ok=false
fi

if [[ "$all_deps_ok" != "true" ]]; then
    echo -e "\n${YELLOW}[!] Some dependencies are missing. See README.md for installation steps.${NC}"
fi

# Collect configuration
echo -e "\n${BLUE}[2/4] Collecting configuration details...${NC}\n"

# Check if .env already exists
SKIP_CONFIG=false
if [[ -f ".env" ]]; then
    echo -e "${YELLOW}[!] .env file already exists. Using existing configuration.${NC}"
    # shellcheck source=/dev/null
    source .env
    SKIP_CONFIG=true
else
    read -rp "Source Dynatrace Tenant URL (https://...): " SOURCE_TENANT_URL
    read -rp "Source API Token: " SOURCE_TENANT_TOKEN
    echo ""
    read -rp "Target Dynatrace Tenant URL (https://...): " TARGET_TENANT_URL
    read -rp "Target API Token: " TARGET_TENANT_TOKEN
fi

# Verify connections
echo -e "\n${BLUE}[3/4] Verifying connections...${NC}"

verify_connection() {
    local url="$1"
    local token="$2"
    local name="$3"

    if curl -s -f -H "Authorization: Api-Token $token" "$url/api/v1/config/clusterversion" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $name tenant"
        return 0
    else
        echo -e "  ${RED}✗${NC} $name tenant"
        return 1
    fi
}

verify_connection "$SOURCE_TENANT_URL" "$SOURCE_TENANT_TOKEN" "Source" || true
verify_connection "$TARGET_TENANT_URL" "$TARGET_TENANT_TOKEN" "Target" || true

# Create .env file
if [[ "$SKIP_CONFIG" != "true" ]]; then
    echo -e "\n${BLUE}[4/4] Creating configuration file...${NC}"

    cat > .env << EOF
# Dynatrace Terraform Configuration
# Created: $(date)

# Source Tenant
SOURCE_TENANT_URL=$SOURCE_TENANT_URL
SOURCE_TENANT_TOKEN=$SOURCE_TENANT_TOKEN

# Target Tenant
TARGET_TENANT_URL=$TARGET_TENANT_URL
TARGET_TENANT_TOKEN=$TARGET_TENANT_TOKEN
EOF

    echo -e "  ${GREEN}✓${NC} Created .env file (${RED}keep this secure!${NC})"
fi

# Installation instructions if Terraform is missing
if ! command -v terraform &> /dev/null; then
    echo -e "\n${YELLOW}[!] Terraform CLI not found. Install it:${NC}"
    echo ""
    echo "  brew tap hashicorp/tap"
    echo "  brew install hashicorp/tap/terraform"
    echo ""
fi

# Python dependencies
if ! python3 -c "import requests" 2>/dev/null; then
    echo -e "\n${YELLOW}[!] Installing Python dependencies...${NC}"
    pip3 install -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
fi

# Summary
echo -e "\n${BLUE}================================================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${BLUE}================================================================${NC}"

echo -e "\n${BLUE}Next Steps:${NC}"
echo ""
echo "1. Verify your configuration:"
echo "   source .env"
echo "   env | grep SOURCE_TENANT"
echo ""
echo "2. Test connectivity (optional):"
echo "   python3 scripts/verify_migration.py"
echo ""
echo "3. Run a dry-run to preview changes:"
echo "   python3 scripts/migrate.py --dry-run"
echo ""
echo "4. Start migration:"
echo "   python3 scripts/migrate.py"
echo ""
echo "Tips:"
echo "   - Use --dry-run to preview changes before applying"
echo "   - Backups are created automatically in config/backups/"
echo "   - Review logs in migration_YYYYMMDD_HHMMSS.log"
echo "   - Use --config-types to migrate specific settings only"
echo ""
