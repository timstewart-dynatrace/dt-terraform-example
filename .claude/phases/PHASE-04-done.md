# Phase 04 -- Reference Currency Directive

Status: DONE

## Goal

Adopt the **Reference Currency directive** pattern from the Best-Practice-Notebooks-Generator project so this codebase has a documented discipline for keeping cited sources current. The single most load-bearing citation today is the **Dynatrace Terraform provider v1.88.0 release-note quote** that defines the auth-routing boundary in `dt_client.py`. If Dynatrace continues to shift that boundary in future provider releases (the trend through v1.88–v1.96 suggests they will), our routing logic needs to follow — and a documented discipline makes that maintenance routine rather than ad-hoc.

## Tasks

- [ ] Create `.claude/rules/reference-currency.md` adapted to this project's surfaces (README, DECISIONS, code docstrings, CHANGELOG) — not the larger Notebooks-Generator surface (notebooks + REFERENCE.md per series). Two directives:
  - **Directive 1 — Next-touch reference standardization.** When editing any file that contains cited URLs, follow the `[Title (publisher)](URL)` minimal format; no marketing taglines; no internal-rule links from user-facing docs; cite the source page (not the docs-assistant summary).
  - **Directive 2 — Deep content verification.** URL liveness via `scripts/validate_citation_urls.py`; spot-check the v1.88.0 boundary against current provider release notes when a refresh PR opens; sprint-cadence scan of Dynatrace whats-new (every 2 weeks).
- [ ] Implement `scripts/validate_citation_urls.py`:
  - Walks all `.md` files in the repo root + `.claude/` tree + `docs/` tree
  - Walks Python docstrings + comments in `pipelines/` for `https://...` URLs
  - Filters placeholder URLs (variable substitutions, all-caps placeholders, example domains)
  - HEAD checks each unique URL via `requests` (already a runtime dep)
  - Writes `docs/citation-status.md` with totals + per-source breakdown + 404 list
  - Exit code: 0 if no 404s, 1 if any (for CI gating once baseline is clean)
- [ ] Wire `.claude/rules/reference-currency.md` into `.claude/CLAUDE.md` `## Rules` "Always active" section
- [ ] Run the validator and commit the initial `docs/citation-status.md` baseline
- [ ] Add `validate_citation_urls.py` invocation note to README's development section
- [ ] Update CHANGELOG `[Unreleased]` with the additions
- [ ] Add DECISIONS.md entry recording the choice + the v1.88.0 boundary as the immediate motivation

## Acceptance Criteria

- New `.claude/rules/reference-currency.md` is concise (<150 lines) and adapted to this project (not a copy of the Notebooks-Generator version)
- `scripts/validate_citation_urls.py` runs from `python3 scripts/validate_citation_urls.py` and produces `docs/citation-status.md`
- Initial run produces a clean baseline: every cited URL in the project is verified live OR documented as a known false positive in the report
- `.claude/CLAUDE.md` `## Rules` section lists `reference-currency.md`
- The Best-Practice-Notebooks-Generator's workflow.md § Reference Currency is referenced in DECISIONS.md as the source of the pattern (not copied silently)

## Decisions Made This Phase

- 2026-05-11 — Reference Currency directive adopted from Best-Practice-Notebooks-Generator (`workflow.md` § Reference Currency in that project). Rationale: the v1.88.0 auth-routing boundary in `dt_client.py` is exactly the kind of vendor-side-shifting citation the directive is designed to keep current. Without a documented discipline, the boundary list goes stale silently and the project's auth routing produces 401s or silent breakage.
- 2026-05-11 — `validate_citation_urls.py` scoped to this project specifically (not a port of the Notebooks-Generator script which scans 446 .ipynb files). Smaller surface (.md + Python source); runs in under a minute; suitable for both local pre-commit runs and CI invocation. Initial implementation does URL HEAD checks only; content-drift detection (page returns 200 but the page has been substantially edited since cite) is deferred — that's a much harder problem and the cite anchoring is mostly to release-note URLs which are immutable.
