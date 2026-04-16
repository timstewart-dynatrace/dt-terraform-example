# Testing Standards

## Test Categories

### Unit Tests
- **Purpose:** Test individual functions (validation, parsing, config generation)
- **Tools:** pytest
- **Location:** `tests/unit/`

### Integration Tests
- **Purpose:** Test migration workflow steps against real or mock Dynatrace APIs
- **Tools:** pytest + requests-mock
- **Location:** `tests/integration/`

### Dry-Run Validation
- **Purpose:** Verify scripts work correctly in dry-run mode without modifying tenants
- **Tools:** Shell execution with `--dry-run` flag
- **Location:** Manual or scripted

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_migrate.py

# Run with coverage
pytest --cov=scripts --cov-report=html

# Run dry-run validation
python3 scripts/migrate.py --dry-run
```

## Test Requirements

### Before Merging
- [ ] All tests pass locally
- [ ] New features have test coverage
- [ ] No test warnings or errors
- [ ] Coverage meets project threshold (80%+)
- [ ] Dry-run mode works without errors
- [ ] Shell scripts pass shellcheck (if installed)

### Test File Naming
- Python: `scripts/migrate.py` -> `tests/test_migrate.py`
- Use descriptive test names: `test_should_validate_token_format`

### Mock & Fixture Guidelines
- Mock Dynatrace API responses for unit tests
- Use fixtures for common test data (environment configs, sample YAML)
- Never use real API tokens in tests
- Clean up temporary files after each test

## Common Issues

| Issue | Fix |
|-------|-----|
| Tests fail with token errors | Ensure tests use mocked tokens, not real .env |
| Terraform not found in test | Mock Terraform CLI calls; don't require binary for unit tests |
| YAML parsing differs | Use consistent PyYAML version across environments |
