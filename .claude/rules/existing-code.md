# Understanding Existing Code

## Before Making Changes

1. **Read the docs first**
   - Each area has its own documentation in `docs/`
   - Docs describe the intended workflow and expected behavior
   - Check `docs/TROUBLESHOOTING.md` for known issues

2. **Trace the flow**
   - Follow the migration workflow: verify -> backup -> download -> validate -> deploy
   - Understand how Python and Shell scripts implement the same workflow
   - Map dependencies between scripts and config files

3. **Look for patterns**
   - Both Python and Shell scripts follow the same 5-step migration workflow
   - Error handling patterns: colored output in Shell, logging in Python
   - Config loading: .env for credentials, environments.yaml for tenant definitions

## Code Review Checklist

When reviewing existing code:
- [ ] Can I understand what this does after 5 minutes?
- [ ] Is the naming clear and consistent?
- [ ] Are error cases handled (missing tokens, network failures, invalid config)?
- [ ] Does it follow the project's dual-implementation pattern?
- [ ] Are credentials handled securely (no hardcoding, .env for secrets)?

## Making Changes Safely

1. **Test with dry-run** before any real migration
2. **Make small changes** that can be verified independently
3. **Test both implementations** if changing shared workflow logic
4. **Document the change** in code, CHANGELOG, and docs

## Refactoring Safely

1. **Preserve behavior** - Don't change what the script does, only how
2. **Test both Python and Shell** - Changes to workflow logic affect both
3. **Review carefully** - Extra scrutiny for token handling and API calls
4. **Communicate intent** - Explain why in commit message

## When Code is Confusing

- [ ] Check git blame for context (`git blame scripts/migrate.py`)
- [ ] Look at related commits for context on why something was added
- [ ] Check `docs/TROUBLESHOOTING.md` -- the workaround may be documented
- [ ] Don't delete "mysterious" code without understanding why it exists
