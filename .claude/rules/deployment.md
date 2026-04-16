# Deployment & Release Checklist

## Pre-Deployment

- [ ] All tests passing
- [ ] Scripts tested with `--dry-run` against a non-production tenant
- [ ] Documentation complete and reviewed
- [ ] CHANGELOG.md updated
- [ ] Version number incremented in `.claude/settings.json`
- [ ] No uncommitted changes
- [ ] No hardcoded credentials or tokens in commits
- [ ] .env.example files updated if new variables added

## Deployment Steps

1. **Tag Release**
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z: brief description"
   git push origin vX.Y.Z
   ```

2. **Verify Package Integrity**
   - All required files present (scripts, docs, config templates)
   - .gitignore prevents credential leakage

3. **Test in Clean Environment**
   ```bash
   # Clone fresh and test
   git clone <repo-url> /tmp/dt-terraform-test
   cd /tmp/dt-terraform-test
   pip install -r requirements.txt
   python3 scripts/migrate.py --dry-run
   ```

## Post-Deployment

- [ ] Verify README quick-start steps work from scratch
- [ ] Check that .env.example files match current variable requirements
- [ ] Update any external documentation or wiki references

## Rollback Procedure

If issues occur:
```bash
# Revert to previous tag
git checkout vX.Y.Z-1
```

Scripts are idempotent and include automatic backup, so target tenant state can be restored from backups created during migration.

## Release Notes Template

```markdown
# Release vX.Y.Z

**Release Date:** YYYY-MM-DD

## What's New
[2-3 line summary of major features/fixes]

## Upgrade Guide
[Any breaking changes or migration steps]

## Changelog
[Link to or paste CHANGELOG section for this version]
```
