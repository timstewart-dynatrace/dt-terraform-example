# Troubleshooting Guide

## Common Issues and Solutions

### Installation Issues

#### Problem: Terraform not found

```bash
$ terraform --version
bash: terraform: command not found
```

**Solution:**
```bash
# Install Terraform
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Verify installation
terraform --version
```

**Solution:**
```bash
# Check if Terraform is in PATH
echo $PATH
which terraform

# Add Homebrew binaries to PATH (Apple Silicon default)
export PATH="$PATH:/opt/homebrew/bin"

# Make it permanent in ~/.zshrc or ~/.bash_profile
echo 'export PATH="$PATH:/opt/homebrew/bin"' >> ~/.zshrc
source ~/.zshrc
```

### Configuration Issues

#### Problem: Missing .env file

```
Error: Missing required arguments
Please provide source and target URLs and API tokens via arguments or .env file
```

**Solution:**
```bash
# Create .env from template
cp config/.env.example .env

# Edit with your actual values
nano .env

# Source the environment
source .env

# Verify variables are set
echo $SOURCE_TENANT_URL
```

#### Problem: Invalid environment variable format

```
Error: Tenant URL is invalid
```

**Solution:**
- Ensure URL format: `https://your-environment-id.live.dynatrace.com`
- No trailing slash
- Check for typos
- Verify the domain is correct

### Authentication Issues

#### Problem: Invalid API Token

```
Error: API returned 401 Unauthorized
```

**Causes and Solutions:**
1. **Token expired**
   - Generate a new token in Dynatrace Settings
   - Update .env file

2. **Insufficient scopes**
   - Token needs these minimum scopes:
     - Source: `config.read`, `dashboards.read`
     - Target: `config.write`, `dashboards.write`
   - Create new token with correct scopes

3. **Wrong token for environment**
   - Verify SOURCE_TENANT_TOKEN goes with SOURCE_TENANT_URL
   - Verify TARGET_TENANT_TOKEN goes with TARGET_TENANT_URL

**Solution:**
```bash
# Check token scopes
curl -H "Authorization: Api-Token YOUR_TOKEN" \
  https://your-tenant.live.dynatrace.com/api/v2/tokens/info | jq '.scopes'

# Should see:
# [
#   "config.read",
#   "dashboards.read",
#  ...
# ]
```

#### Problem: Connection refused

```
Error: Connection refused
Could not connect to tenant
```

**Solutions:**
1. **Check URL is correct**
   ```bash
   curl -I https://your-tenant.live.dynatrace.com
   ```

2. **Check network connectivity**
   ```bash
   ping your-tenant.live.dynatrace.com
   ```

3. **Check for proxies or firewalls**
   - If behind corporate proxy, configure:
   ```bash
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

### Configuration Download Issues

#### Problem: No configuration found

```
Error: No configuration found to download
Downloaded 0 items
```

**Possible causes:**
- Source tenant has no configuration
- Specified config types don't exist
- API token missing required scopes

**Solution:**
```bash
# Verify token scopes
curl -H "Authorization: Api-Token YOUR_TOKEN" \
  https://your-tenant.live.dynatrace.com/api/v2/tokens/info | \
  jq '.scopes | map(select(test("config|dashboard")))'

# List supported config types and retry with a smaller subset
python3 scripts/migrate.py --list-types
python3 scripts/migrate.py --config-types dashboard
```

#### Problem: YAML parsing error

```
Error: Unable to parse YAML file
mapping values are not allowed here
```

**Solution:**
- Check indentation (must be 2 spaces, not tabs)
- Ensure all colons have spaces after them
- Verify quotes are balanced
- Use a YAML validator:
  ```bash
  python3 -c "import yaml; yaml.safe_load(open('file.yaml'))"
  ```

### Deployment Issues

#### Problem: Configuration deployment failed

```
Error: Failed to apply configuration
Invalid configuration
```

**Solutions:**
1. **Validate configuration before deploying**
   ```bash
   python3 scripts/migrate.py --dry-run
   ```

2. **Check configuration compatibility**
   - Target tenant might not support certain settings
   - Review error logs for specific issues

3. **Check target tenant permissions**
   - Verify token has `config.write` scope
   - Ensure token is not expired

#### Problem: Partial deployment

```
Deployed 5 of 10 dashboards
Error: Failed to deploy dashboard-06
```

**Solutions:**
1. **Review the specific dashboard configuration**
   ```bash
   cat config/source/dashboards/dashboard-06.yaml
   ```

2. **Validate against target tenant**
   - Some configuration might be incompatible
   - Check Dynatrace version differences

3. **Deploy manually for problem dashboards**
   ```bash
   # Retry with only dashboard type to isolate failing resources
   python3 scripts/migrate.py --config-types dashboard --dry-run
   python3 scripts/migrate.py --config-types dashboard
   ```

### Performance Issues

#### Problem: Slow download

```
Downloading configuration... (taking very long)
```

**Solutions:**
1. **Check network connectivity**
   ```bash
   ping your-tenant.live.dynatrace.com
   ```

2. **Reduce scope using --config-types**
   ```bash
   # Instead of downloading everything
   python3 scripts/migrate.py --config-types dashboard
   ```

3. **Run at off-peak hours**
   - Migrations consume API quota
   - Schedule for when API load is lower

#### Problem: API quota exceeded

```
Error 429: Too Many Requests
```

**Solution:**
```bash
# Wait 15-20 minutes for quota reset
# Then resume migration

# To avoid quota issues in future:
# - Use smaller batches
# - Add delays between requests
# - Download only necessary config types
```

### Logging and Diagnostics

#### Enable Debug Logging

```bash
# Enable verbose output
TERRAFORM_LOG=DEBUG python3 scripts/migrate.py

# Or with shell script
bash -x scripts/migrate.sh
```

#### Check Migration Logs

```bash
# Find most recent migration log
ls -lt migration_*.log | head -1

# View with colorized output
cat migration_20240101_120000.log | less -R

# Search for errors
grep ERROR migration_*.log
grep "Error" migration_*.log
```

#### Review Backup

```bash
# List all backups
ls -la config/backups/

# Compare with current configuration
diff -r config/backups/20240101_000000/dashboards/ \
        config/source/dashboards/
```

### When Everything Fails

#### Collect Diagnostic Information

```bash
#!/bin/bash
# Run this to collect diagnostic info for support

echo "=== System Information ===" 
sw_vers
which terraform
terraform --version
which python3
python3 --version

echo ""
echo "=== Environment Variables ===" 
env | grep -i dynatrace | head -20

echo ""
echo "=== Connectivity Test ===" 
curl -s -I https://your-tenant.live.dynatrace.com | head -5

echo ""
echo "=== Recent Logs ===" 
head -50 migration_*.log
```

#### Create Issue Report

When reporting an issue, include:
1. **Full error message** (copy-paste)
2. **Steps to reproduce**
3. **Environment information** (from diagnostic script above)
4. **Configuration files** (sanitize API tokens!)
5. **Log files** (last 100 lines)

Example:
```markdown
**Issue:** Configuration deployment fails with YAML error

**Steps to Reproduce:**
1. Run `python3 scripts/migrate.py`
2. Configuration downloads successfully
3. Deployment fails with error

**Error Message:**
```
Error: mapping values are not allowed here
  in "config/source/dashboards/dashboard.yaml", line 25
```

**Environment:**
- macOS 14.2
- Terraform 1.8.5
- Python 3.11.6

**Logs:** 
[attachment: migration.log]
```

## Getting Help

### Resources
- [Repository Issues](https://github.com/timstewart-dynatrace/dt-terraform-example/issues)
- [Dynatrace Terraform Provider](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest)
- [Dynatrace Community Forums](https://community.dynatrace.com/)
- [Dynatrace API Documentation](https://www.dynatrace.com/support/help/dynatrace-api)

### Open an Issue on GitHub

```bash
# Before opening an issue, check:
# 1. Similar issues don't already exist
# 2. You have latest version of Terraform CLI and dependencies
# 3. You have collected diagnostic information

# Create a GitHub issue with:
# - Clear title describing the problem
# - Detailed description (see example above)
# - Steps to reproduce
# - Logs and relevant configuration (sanitized)
```
