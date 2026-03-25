# Dynatrace Terraform Configuration Migration

This project provides Python and Shell tools for cloning and migrating Dynatrace configuration between tenants using Terraform-compatible workflows.

## Overview

The scripts in this repository orchestrate source export, validation, backup, and target deployment while working with Terraform-oriented configuration structures.

## Prerequisites

- **Terraform CLI 1.5+**
- **Git**
- **Python 3.8+** (for Python scripts)
- Dynatrace tenant(s) with API access
- API tokens for both source and target tenants

## Installation

### 1. Install Terraform

Check your current Terraform version:

```bash
terraform --version
```

If Terraform is not installed on macOS:

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Source tenant
SOURCE_TENANT_URL=https://your-source-tenant.live.dynatrace.com
SOURCE_TENANT_TOKEN=your-source-api-token

# Target tenant
TARGET_TENANT_URL=https://your-target-tenant.live.dynatrace.com
TARGET_TENANT_TOKEN=your-target-api-token
```

## Project Structure

```
.
├── README.md                      # This file
├── .env                           # Environment variables (create this)
├── config/                        # Terraform-oriented migration files
│   ├── environments.yaml          # Environment definitions
│   └── tenants/                   # Tenant-specific configs
├── scripts/
│   ├── migrate.py                 # Python migration script
│   ├── migrate.sh                 # Shell script migration
│   └── clone-config.sh            # Clone configuration helper
└── docs/                          # Additional documentation
```

## Usage

### Using the Python Script

```bash
python scripts/migrate.py \
  --source https://source-tenant.live.dynatrace.com \
  --target https://target-tenant.live.dynatrace.com \
  --source-token YOUR_SOURCE_TOKEN \
  --target-token YOUR_TARGET_TOKEN
```

### Using the Shell Script

```bash
./scripts/migrate.sh \
  --source-url https://source-tenant.live.dynatrace.com \
  --target-url https://target-tenant.live.dynatrace.com \
  --source-token YOUR_SOURCE_TOKEN \
  --target-token YOUR_TARGET_TOKEN
```

### Using Environment Variables

```bash
source .env
python scripts/migrate.py
```

## Configuration Files

Edit `config/environments.yaml` to define your tenants:

```yaml
environments:
  source:
    name: source-tenant
    url: https://source-tenant.live.dynatrace.com
    token: ${SOURCE_TENANT_TOKEN}
  
  target:
    name: target-tenant
    url: https://target-tenant.live.dynatrace.com
    token: ${TARGET_TENANT_TOKEN}
```

## Features

- ✅ Clone configuration from source to target tenant
- ✅ Support for all Dynatrace configuration types
- ✅ Dry-run mode to preview changes
- ✅ Validation before deployment
- ✅ Rollback capabilities
- ✅ Detailed logging

## Getting API Tokens

1. Go to your Dynatrace tenant
2. Navigate to **Settings** → **Integration** → **Dynatrace API**
3. Create a new token with the following scopes:
   - Read configuration (`config.read`)
   - Write configuration (`config.write`)
   - Read Dashboards (`dashboards.read`)
   - Write Dashboards (`dashboards.write`)
   - And other necessary scopes based on your use case

## Troubleshooting

### "terraform: command not found"

Ensure Terraform is installed and available in your PATH:
```bash
which terraform
terraform --version
```

### "Invalid API token"

- Verify your tokens are correct
- Check that tokens have the necessary scopes
- Ensure tokens haven't expired

### "Configuration validation failed"

- Check the error messages in the logs
- Verify your configuration YAML is properly formatted
- Ensure all required fields are present

## References

- [Dynatrace Terraform Provider](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest)
- [Dynatrace API Documentation](https://www.dynatrace.com/support/help/dynatrace-api)
- [Configuration as Code Best Practices](https://www.dynatrace.com/support/help/how-to-use-dynatrace/configuration-management/configuration-as-code)

## License

MIT
