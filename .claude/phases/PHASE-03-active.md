# Phase 03 -- Pytest Coverage for Combined Auth + CI

Status: ACTIVE

## Goal

Lock down the Phase 02 combined-auth logic with formal pytest coverage. Add a CI workflow so future PRs run the tests automatically. Today the project has zero tests — the combined-auth routing is exactly the kind of branching logic that benefits from test coverage, and PR #8's smoke tests were one-shot in-session, not committed.

## Tasks

- [ ] Add `requirements-dev.txt` with `pytest`, `pytest-cov`, `responses` (for HTTP-level tests)
- [ ] Add `pyproject.toml` (or `pytest.ini`) configuring pytest's `testpaths`, `python_files`, coverage source
- [ ] Create `tests/` directory with `__init__.py` and `conftest.py`
- [ ] `tests/test_auth_header.py` — covers `_header_for_token`: dt0s16 / dt0s01 → Bearer; dt0c01 → Api-Token; unknown prefix → Api-Token fallback
- [ ] `tests/test_auth_routing.py` — covers `_needs_classic_api_token`: positive cases (10+ patterns from the v1.88.0 exclusion list) + negative cases (non-excluded endpoints: dashboards, alerting profiles, MZs, Settings 2.0)
- [ ] `tests/test_dt_client_auth.py` — covers `DynatraceClient._auth_header_for_url`: backward-compat (classic-only); Platform-only on non-excluded works; Platform-only on excluded raises `MissingClassicTokenError`; combined auth routes correctly; error message contains the URL path and remediation
- [ ] `tests/test_tenant_config.py` — covers `TenantConfig.api_token` default is None; both fields settable
- [ ] `tests/test_config_loader.py` — covers `PipelineConfig.get_source_tenant()` / `get_target_tenant()` reads from env vars (`SOURCE_TENANT_API_TOKEN`, `TARGET_TENANT_API_TOKEN`) and from `pipeline.yaml`; back-compat when no `_API_TOKEN` set returns `api_token=None`
- [ ] `.github/workflows/test.yml` — runs `pytest` on PR and push to main; matrix: Python 3.9, 3.11, 3.12
- [ ] Update `requirements.txt` README mention to point at `requirements-dev.txt` for development setup
- [ ] Update `CHANGELOG.md` `[Unreleased]` with the tests + CI additions
- [ ] Update `DECISIONS.md` with the testing-stack decision (pytest + responses)

## Acceptance Criteria

- `pip install -r requirements-dev.txt && pytest` runs all tests, all green
- Coverage report shows ≥ 95% line coverage of `pipelines/core/dt_client.py` (the auth routing logic) and ≥ 80% of `pipelines/core/types.py` and `pipelines/core/config.py`
- New `.github/workflows/test.yml` runs successfully on the PR for this phase
- `MissingClassicTokenError` error message explicitly tested for: (a) names the failing URL path, (b) names the env var to set
- All 6 smoke-test scenarios from the Phase 02 PR description are now formal tests (replacing the in-session checks)

## Decisions Made This Phase

- 2026-05-11 — pytest chosen over unittest. Pytest is the de-facto Python testing standard in 2026; the fixtures + parametrize features keep the test code compact, especially for the URL-pattern matching (one parametrize → many assertions).
- 2026-05-11 — `responses` library chosen for HTTP-level mocking (vs `unittest.mock` directly on `requests.Session`). `responses` registers expected URL + method + response and produces clearer failure messages when the request doesn't match — useful for a project whose primary risk surface is "did we send the right Authorization header to the right URL?"
- 2026-05-11 — Three Python versions in CI matrix (3.9, 3.11, 3.12). 3.9 matches the project's stated minimum from README. 3.11 is the modern stable; 3.12 catches forward-compat issues without going to 3.13 yet (less ecosystem coverage).
