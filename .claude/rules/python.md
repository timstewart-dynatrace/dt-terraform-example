# Python Development Standards

## Python Version & Environment

- **Target Version:** Python 3.8+ (specified in README)
- **Virtual Environment:** Always use venv for isolation
- **Dependency Management:** Use requirements.txt

## Code Style & Conventions

### Naming Conventions
```python
# Functions and variables: snake_case
def validate_token_scopes():
    pass

tenant_url = "https://abc.live.dynatrace.com"

# Classes: PascalCase
class MigrationConfig:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Private methods/attributes: _leading_underscore
def _parse_environment_yaml():
    pass
```

### Code Organization
- Group related functions in modules
- Keep functions under 50 lines (complex logic in helper functions)
- Alphabetical or logical order of imports

### Type Hints (REQUIRED)
```python
def download_config(tenant_url: str, token: str, output_dir: str = "./config") -> bool:
    """Download configuration from a Dynatrace tenant."""
    pass
```

## Imports

```python
# Order: Standard library -> Third-party -> Local
import os
import logging
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

from .config import load_environment
```

## Error Handling

```python
# Be specific about exceptions
try:
    response = requests.get(f"{tenant_url}/api/v2/settings", headers=headers)
    response.raise_for_status()
except requests.exceptions.ConnectionError:
    logger.error(f"Cannot connect to tenant: {tenant_url}")
    raise
except requests.exceptions.HTTPError as e:
    logger.error(f"API error: {e.response.status_code}")
    raise
```

## Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Downloading config type: %s", config_type)
logger.info("Migration started for tenant: %s", tenant_url)
logger.warning("Config type %s returned empty response", config_type)
logger.error("Failed to deploy configuration: %s", error_msg)
```

## Testing Requirements

### Test File Naming
- `scripts/migrate.py` -> `tests/test_migrate.py`
- Test class: `class TestMigration`
- Test method: `def test_should_validate_token_format`

### Running Tests
```bash
pytest tests/ -v
pytest --cov=scripts --cov-report=html
pytest -x  # Stop on first failure
```

## Shell Script Standards

Since this project includes Bash scripts alongside Python:

- Use `set -euo pipefail` at the top of every script
- Quote all variable expansions: `"${VAR}"`
- Use functions for reusable logic
- Include `--help` / usage output
- Use colored output for user-facing messages (with fallback for non-TTY)
- Run `shellcheck` when available

## Dependencies Management

### Adding Dependencies
```bash
pip install package_name
pip freeze > requirements.txt
```

### Virtual Environment
- Always activate: `source venv/bin/activate`
- Don't commit venv folder (already in .gitignore)
- On fresh clone: `python3 -m venv venv && pip install -r requirements.txt`
