# Core & Workflow Rules

## Phase Management [For Multi-Phase Work]

For implementations spanning 3+ phases, use this system:

### Phase File Structure
```
.claude/phases/
  PHASE-01-done.md       (rename when complete)
  PHASE-02-active.md     <- only ONE active at a time
  PHASE-03-pending.md
```

### Phase File Format
```markdown
# Phase 02 -- [Feature Name]
Status: ACTIVE | PENDING | DONE

## Goal
One sentence. What does completing this phase deliver?

## Tasks
- [ ] Task 1
- [ ] Task 2

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Decisions Made This Phase
<!-- Log here as you go, then move to DECISIONS.md -->
```

### Rules
- One active phase at a time (never start next phase without explicit approval)
- Re-read active phase file when context refills (don't rely on chat history)
- If plan needs to change, ask explicitly before changing it
- Phase files contain goals/tasks only -- no code snippets
- Rename `PHASE-02-active.md` -> `PHASE-02-done.md` when complete

## Decision Logging

Log non-trivial technical decisions to `.claude/DECISIONS.md`.

### What to Log
- Choosing library/framework over alternatives
- Choosing architecture pattern
- Rejecting a common approach and why
- Any decision made under time pressure or uncertainty

### What NOT to Log
- Implementation details
- Decisions with only one reasonable option
- Stylistic choices already covered by rules

### Format
```markdown
## YYYY-MM-DD -- [Title]

**Chosen:** What was decided
**Alternatives:** What else was considered
**Why:** Full reasoning -- be specific, not generic
**Trade-offs:** What is lost or risked with this choice
**Revisit if:** Condition under which this should be reconsidered
```

### Rules
- Log at the time decision is made, not retroactively
- If user made the call, prefix with "User decision:" for context
- Decisions are append-only -- don't edit past entries, add new entry if something changes

## Git Workflow

### Branching Strategy

Never commit directly to `main`. Every change requires a feature branch + PR.

### Branch Naming
- Lowercase, hyphen-separated, max 50 characters
- Start with type: `feature/`, `fix/`, `refactor/`, `chore/`

```bash
feature/add-validation-step
fix/token-scope-error
refactor/split-migration-phases
chore/update-dependencies
```

### Branch Cleanup
Delete after merge (both remote and local):
```bash
git push origin --delete feature/branch-name
git branch -d feature/branch-name
```

### Commit Messages -- Conventional Commits [MUST]

Format:
```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

**Types:**

| Type | When | Example |
|------|------|---------|
| `feat` | New feature/capability | `feat(migration): add selective config type export` |
| `fix` | Bug fix | `fix(deploy): handle expired token gracefully` |
| `refactor` | Code change, no behavior change | `refactor(migrate): extract validation logic` |
| `chore` | Dependencies, build, tooling | `chore(deps): upgrade requests to 2.32` |
| `docs` | Documentation only | `docs(readme): add troubleshooting section` |
| `test` | Adding/fixing tests | `test(migrate): add dry-run validation tests` |
| `perf` | Performance improvement | `perf(download): parallelize config download` |
| `style` | Formatting, no logic change | `style(scripts): normalize shell formatting` |

### Merge Commits

Use `--no-ff` to preserve branch history:
```bash
git merge --no-ff feature/branch-name
```

### Documentation - MANDATORY

**ALL features MUST be documented BEFORE merging to main**

Documentation checklist:
- [ ] README.md - Update if user-facing changes
- [ ] CHANGELOG.md - Add entry following Keep a Changelog format
- [ ] Code comments and docstrings for new functions/classes
- [ ] Architecture docs updated if design changed
- [ ] docs/*.md updated if workflow changes

### Version Management

**ALL merges to main that add features or fixes MUST increment the version number.**

Follow [Semantic Versioning 2.0.0](https://semver.org/):
- **MAJOR** (X.0.0) - Incompatible API changes
- **MINOR** (0.X.0) - New features (backwards-compatible)
- **PATCH** (0.0.X) - Bug fixes (backwards-compatible)

Version bump checklist:
- [ ] Version incremented in `.claude/settings.json`
- [ ] CHANGELOG.md updated with changes
- [ ] Git tag created: `git tag -a vX.Y.Z -m "Release message"`

### CHANGELOG Format

Always follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format:

```markdown
## [Unreleased]

## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Fixed
- Bug fixes

### Removed
- Removed features
```

## Code Organization Principles

1. **Single Responsibility** - Each script/function should have one clear purpose
2. **DRY (Don't Repeat Yourself)** - Extract common patterns into reusable functions
3. **Clear Naming** - Variable/function names should be self-documenting
4. **Comments** - Explain the "WHY", not the "WHAT" (code shows what it does)
5. **Documentation** - Keep docs near code; update simultaneously

## Review Standards

Before submitting for review:
- [ ] Code follows project style guide
- [ ] Scripts run successfully with `--dry-run`
- [ ] No merge conflicts
- [ ] Documentation complete
- [ ] No commented-out code left behind
- [ ] No secrets/credentials in commits
