# Getting Started with Dynatrace Terraform Migration

## Quick Start (5 minutes)

### 1. Install Terraform

```bash
# Install Terraform (macOS)
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Verify
terraform --version
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp config/.env.example .env

# Edit .env with your actual tenant URLs and API tokens
nano .env
```

Get your API tokens:
1. Go to **Settings** → **Integration** → **Dynatrace API**
2. Create a new token with scopes:
   - `config.read` (source tenant)
   - `config.write` (target tenant)
   - `dashboards.read` (source)
   - `dashboards.write` (target)

### 3. Run the Migration

#### Using Python (Recommended)

```bash
# Install dependencies
pip3 install -r requirements.txt

# Test with dry-run first
python3 scripts/migrate.py --dry-run

# Run the actual migration
python3 scripts/migrate.py
```

#### Using Shell Script

```bash
# Make script executable
chmod +x scripts/migrate.sh

# Test with dry-run first
./scripts/migrate.sh --dry-run

# Run the actual migration
./scripts/migrate.sh
```

## Configuration Types

This project supports migrating these configuration types:

- **Dashboard configurations**: `dashboard`
- **Alerting**: `alerting-profiles`, `notification`
- **Tagging**: `auto-tag`
- **Metrics**: `calculated-metrics-service`, `calculated-metrics-log`
- **Detection Rules**: `app-detection-rule`, `service-detection-rule`
- **Management**: `management-zone`
- **Monitoring**: `extension`, `host-monitoring-advanced-configuration`
- **Synthetic**: `synthetic-monitor`, `synthetic-location`
- **Settings**: `settings`

## Advanced Usage

### Migrate Specific Configuration Types

```bash
# Using Python
python3 scripts/migrate.py --config-types dashboard,alerting-profiles,management-zone

# Using Shell
./scripts/migrate.sh --config-types dashboard,alerting-profiles,management-zone
```

### Dry-Run Mode (Preview Changes)

```bash
# Using Python
python3 scripts/migrate.py --dry-run

# Using Shell
./scripts/migrate.sh --dry-run
```

### Skip Backup

```bash
# Using Python
python3 scripts/migrate.py --no-backup  # Note: not available in Python version

# Using Shell
./scripts/migrate.sh --no-backup
```

### Custom Configuration Directory

```bash
# Using Python
python3 scripts/migrate.py --config-dir /path/to/config

# Using Shell
./scripts/migrate.sh --config-dir /path/to/config
```

## Troubleshooting

### Terraform Command Not Found

```bash
# Check if Terraform is in PATH
which terraform

# If not found, add to PATH
export PATH="$PATH:/opt/homebrew/bin"

# Make it permanent (add to ~/.zshrc or ~/.bash_profile)
echo 'export PATH="$PATH:/opt/homebrew/bin"' >> ~/.zshrc
```

### Terraform Not Installed

```bash
# Install Terraform
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Check Terraform version
terraform --version
```

### API Token Invalid

1. Verify token is not expired
2. Check token has required scopes
3. Ensure URL is correct (no trailing slash)

### Configuration Validation Failed

```bash
# Check if YAML files are valid
python3 -c "import yaml; yaml.safe_load(open('config/source/dashboards.yaml'))"

# Check for common YAML issues:
# - Missing colons after keys
# - Incorrect indentation
# - Unquoted special characters
```

## Backup Location

Backups are stored in: `config/backups/YYYYMMDD_HHMMSS/`

To restore from backup:
```bash
python3 scripts/migrate.py --config-dir config/backups/20240101_120000
```

## Project Structure

```
.
├── .env                        # Environment variables (create from .env.example)
├── README.md                   # Main documentation
├── requirements.txt            # Python dependencies
├── config/
│   ├── .env.example           # Template for environment variables
│   ├── environments.yaml       # Terraform migration environment configuration
│   ├── source/                # Downloaded source configuration
│   ├── target/                # Target configuration (if downloaded)
│   └── backups/               # Automatic backups timestamped
├── scripts/
│   ├── migrate.py            # Python migration script
│   ├── migrate.sh            # Shell migration script
│   └── clone-config.sh       # Helper script for cloning
└── docs/
    ├── GETTING_STARTED.md     # This file
    ├── ADVANCED.md            # Advanced configurations
    └── TROUBLESHOOTING.md     # Common issues and solutions
```

## Related Resources

- [Dynatrace Terraform Provider](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest)
- [Dynatrace API Documentation](https://www.dynatrace.com/support/help/dynatrace-api)
- [Configuration as Code overview (DT docs)](https://docs.dynatrace.com/docs/deliver/configuration-as-code)

## Support

For issues or questions:
1. Check the TROUBLESHOOTING.md file
2. Review the Dynatrace Terraform provider documentation
3. Check the Dynatrace Community Forums
4. Open an issue in this repository
