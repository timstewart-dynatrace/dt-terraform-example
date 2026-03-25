# Advanced Configuration and Usage

## Environment-Specific Configuration

### Multiple Tenants Setup

If you need to manage multiple source/target pairs, create separate environment configurations:

```bash
# Create configs for different environments
config/
├── environments-prod.yaml
├── environments-staging.yaml
└── environments-dev.yaml
```

**config/environments-prod.yaml:**
```yaml
environments:
  source:
    name: prod-source
    url: https://prod-source.live.dynatrace.com
    token: ${PROD_SOURCE_TOKEN}
  target:
    name: prod-target
    url: https://prod-target.live.dynatrace.com
    token: ${PROD_TARGET_TOKEN}
```

Use it with:
```bash
python3 scripts/migrate.py --config-file config/environments-prod.yaml
```

## Configuration Filtering

### Migrate Only Specific Configuration Types

```bash
# Dashboards only
python3 scripts/migrate.py --config-types dashboard

# Multiple types
python3 scripts/migrate.py --config-types dashboard,alerting-profiles,management-zone

# Exclude certain types (requires custom script)
```

## Pre-Migration Validation

### Validate Connectivity

```bash
#!/bin/bash
# validate_connectivity.sh

SOURCE_URL="${1}"
SOURCE_TOKEN="${2}"

curl -s -H "Authorization: Api-Token ${SOURCE_TOKEN}" \
  "${SOURCE_URL}/api/v2/environments" | jq '.'
```

### Check Token Scopes

```bash
#!/bin/bash
# check_token_scopes.sh

TENANT_URL="${1}"
TOKEN="${2}"

curl -s -H "Authorization: Api-Token ${TOKEN}" \
  "${TENANT_URL}/api/v2/tokens/info" | jq '.scopes'
```

## Post-Migration Validation

### Verify Configuration Was Applied

```python
#!/usr/bin/env python3
"""
Verify that configuration was successfully migrated.
Compares dashboard counts, alerting profiles, etc. between source and target.
"""

import requests
import json
from typing import Dict

def get_config_summary(url: str, token: str) -> Dict:
    """Get a summary of configuration in a tenant."""
    headers = {'Authorization': f'Api-Token {token}'}
    
    summary = {}
    
    # Count dashboards
    dashboards = requests.get(
        f'{url}/api/v2/dashboards',
        headers=headers,
        timeout=10
    ).json()
    summary['dashboards'] = len(dashboards.get('dashboards', []))
    
    # Count alerting profiles
    profiles = requests.get(
        f'{url}/api/v2/alertingProfiles',
        headers=headers,
        timeout=10
    ).json()
    summary['alerting_profiles'] = len(profiles.get('alertingProfiles', []))
    
    # Count management zones
    zones = requests.get(
        f'{url}/api/v2/managementZones',
        headers=headers,
        timeout=10
    ).json()
    summary['management_zones'] = len(zones.get('managementZones', []))
    
    return summary

def compare_tenants(source_url: str, source_token: str, 
                   target_url: str, target_token: str) -> Dict:
    """Compare configuration between source and target."""
    
    source = get_config_summary(source_url, source_token)
    target = get_config_summary(target_url, target_token)
    
    print("Configuration Comparison:")
    print(f"{'Configuration':<25} {'Source':<10} {'Target':<10} {'Match':<10}")
    print("-" * 55)
    
    for config_type, source_count in source.items():
        target_count = target.get(config_type, 0)
        match = "✓" if source_count == target_count else "✗"
        print(f"{config_type:<25} {source_count:<10} {target_count:<10} {match:<10}")
    
    return source == target

if __name__ == '__main__':
    import sys
    import os
    
    source_url = os.getenv('SOURCE_TENANT_URL')
    source_token = os.getenv('SOURCE_TENANT_TOKEN')
    target_url = os.getenv('TARGET_TENANT_URL')
    target_token = os.getenv('TARGET_TENANT_TOKEN')
    
    if not all([source_url, source_token, target_url, target_token]):
        print("Error: Missing environment variables")
        sys.exit(1)
    
    success = compare_tenants(source_url, source_token, target_url, target_token)
    sys.exit(0 if success else 1)
```

## Continuous Integration / CD Integration

### GitHub Actions Workflow

**.github/workflows/migrate-config.yml:**
```yaml
name: Migrate Dynatrace Configuration

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to migrate to'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  migrate:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.8.5
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Python dependencies
        run: pip install -r requirements.txt
      
      - name: Run migration
        env:
          SOURCE_TENANT_URL: ${{ secrets.SOURCE_TENANT_URL }}
          SOURCE_TENANT_TOKEN: ${{ secrets.SOURCE_TENANT_TOKEN }}
          TARGET_TENANT_URL: ${{ secrets.TARGET_TENANT_URL }}
          TARGET_TENANT_TOKEN: ${{ secrets.TARGET_TENANT_TOKEN }}
        run: python3 scripts/migrate.py
      
      - name: Verify migration
        env:
          SOURCE_TENANT_URL: ${{ secrets.SOURCE_TENANT_URL }}
          SOURCE_TENANT_TOKEN: ${{ secrets.SOURCE_TENANT_TOKEN }}
          TARGET_TENANT_URL: ${{ secrets.TARGET_TENANT_URL }}
          TARGET_TENANT_TOKEN: ${{ secrets.TARGET_TENANT_TOKEN }}
        run: python3 scripts/verify_migration.py
```

## Handling Configuration Conflicts

### When Target Has Configuration Not in Source

1. **Option 1: Preserve Target Configuration**
   - Don't deploy conflicting configurations
   - Manually merge/review
   - Deploy only non-conflicting elements

2. **Option 2: Overwrite (Use with Caution!)**
   ```bash
   python3 scripts/migrate.py --force-overwrite
   ```

3. **Option 3: Manual Merge**
   - Download both source and target configs
   - Review differences using a diff tool
   - Manually select which configs to deploy

### Diff Between Tenants

```bash
# Download both configurations
./scripts/clone-config.sh --tenant source --output /tmp/source_config
./scripts/clone-config.sh --tenant target --output /tmp/target_config

# Compare
diff -r /tmp/source_config /tmp/target_config
```

## Performance Optimization

### Parallel Uploads (for large configurations)

If uploading large numbers of dashboards, alerting profiles, etc., you can modify the migration scripts to use parallel uploads:

```python
from concurrent.futures import ThreadPoolExecutor
import time

def deploy_parallel(config_files: List[str], max_workers: int = 5):
    """Deploy multiple configuration files in parallel."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(deploy_file, f) for f in config_files]
        results = [f.result() for f in futures]
    return all(results)
```

## Scheduled Migrations

### Cron Job Setup

```bash
# Edit crontab
crontab -e

# Add scheduled migration (daily at 2 AM)
0 2 * * * cd /Users/tim.stewart/GitHub/terraform && \
  source .env && \
  python3 scripts/migrate.py >> logs/migration.log 2>&1
```

### Log Rotation

```bash
mkdir -p logs

# Add to crontab for log cleanup
0 3 * * 7 find /Users/tim.stewart/GitHub/terraform/logs -name "*.log" -mtime +30 -delete
```

## Security Best Practices

1. **Never commit tokens to git**
   - Use .env files (add to .gitignore)
   - Use environment variables
   - Use CI/CD secret management

2. **Restrict token scopes**
   - Source: read-only scopes
   - Target: write-specific scopes
   - Create separate tokens for different environments

3. **Audit trail**
   - Keep migration logs
   - Store backups securely
   - Review changes before deploying

4. **.gitignore**
```
.env
*.log
config/source/
config/target/
config/backups/
```

## Rolling Back

If something goes wrong:

```bash
# Option 1: Restore from backup
python3 scripts/migrate.py --config-dir config/backups/YYYYMMDD_HHMMSS

# Option 2: Re-apply backup snapshot through migration workflow
python3 scripts/migrate.py --config-dir config/backups/YYYYMMDD_HHMMSS

# Option 3: Keep previous configuration and investigate
# Review logs in ./migration_YYYYMMDD_HHMMSS.log
```

## Troubleshooting in More Detail

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting steps.
