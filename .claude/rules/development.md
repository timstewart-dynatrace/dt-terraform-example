# Development Setup & Tech Stack

## Prerequisites

- Python 3.8+ (verify with `python3 --version`)
- Bash 4.0+ (verify with `bash --version`)
- Terraform CLI 1.5+ (verify with `terraform --version`)
- curl and jq (for shell scripts)
- pip (included with Python)

## Initial Setup

```bash
# Install Terraform (macOS)
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Set up environment
cp config/.env.example .env
nano .env  # Add your tenant URLs and tokens
source .env

# Install Python dependencies
pip install -r requirements.txt
```

## Development Workflow

### Common Tasks

| Task | Command | Purpose |
|------|---------|---------|
| Run migration (Python) | `python3 scripts/migrate.py` | Full tenant migration |
| Run migration (Shell) | `./scripts/migrate.sh` | Full tenant migration |
| Dry run (Python) | `python3 scripts/migrate.py --dry-run` | Preview without changes |
| Dry run (Shell) | `./scripts/migrate.sh --dry-run` | Preview without changes |
| Selective migration | `python3 scripts/migrate.py --config-types dashboard` | Migrate specific types |
| List config types | `python3 scripts/migrate.py --list-types` | Show supported types |
| Clone config | `./scripts/clone-config.sh` | Download config to timestamped dir |
| Verify migration | `python3 scripts/verify_migration.py` | Compare source/target counts |
| Run setup wizard | `./setup.sh` | Interactive dependency check and .env setup |
| Run linter | `ruff check .` | Check Python code quality |
| Format code | `ruff format .` | Auto-format Python code |
| Type check | `mypy scripts/` | Static type analysis |
| Run tests | `pytest tests/ -v` | Run test suite |

## Tech Stack Overview

### Dependencies
- **requests** - HTTP client for Dynatrace API calls
- **PyYAML** - Parse environment configuration files
- **python-dotenv** - Load credentials from .env files securely

### Tools & Infrastructure
- **Terraform CLI** - Dynatrace configuration-as-code tool
- **curl/jq** - Shell-based API interaction and JSON processing
- **Linting** - ruff (Python)
- **Type Checking** - mypy (Python)
- **Testing** - pytest

## Project Structure Reference

```
dt-terraform-example/
├── scripts/                 # Migration and utility scripts (Python + Shell)
├── config/                  # Environment configs and templates
├── docs/                    # User-facing documentation
├── .claude/                 # AI assistant instructions
├── README.md                # User-facing overview
├── CHANGELOG.md             # Version history
└── .gitignore               # Git ignore rules
```

## Troubleshooting Setup

| Issue | Solution |
|-------|----------|
| `terraform: command not found` | Install via Homebrew and add to PATH |
| `ModuleNotFoundError` | Activate venv; reinstall: `pip install -r requirements.txt` |
| `Invalid API token` | Check token scopes match requirements in docs |
| `Permission denied` on script | `chmod +x scripts/*.sh` |
| Shell script fails on macOS | Ensure Bash 4.0+ (`brew install bash`) |

## Environment Variables

Create `.env` from template or export directly:

| Variable | Purpose | Example |
|----------|---------|---------|
| `SOURCE_TENANT_URL` | Source Dynatrace tenant URL | `https://abc12345.live.dynatrace.com` |
| `SOURCE_TENANT_TOKEN` | Source tenant API token | `dt0c01.xxxx.yyyy` |
| `TARGET_TENANT_URL` | Target Dynatrace tenant URL | `https://def67890.live.dynatrace.com` |
| `TARGET_TENANT_TOKEN` | Target tenant API token | `dt0c01.xxxx.yyyy` |
| `CONFIG_DIR` | Custom config directory (optional) | `./config` |
