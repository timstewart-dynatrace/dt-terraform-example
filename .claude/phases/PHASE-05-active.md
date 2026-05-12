# Phase 05 -- Test Coverage Expansion (Deploy/Export Pipelines + Validator)

Status: ACTIVE

## Goal

Phase 03 scoped tightly to auth-routing logic (`dt_client._auth_header_for_url`, `_header_for_token`, `_needs_classic_api_token`, `TenantConfig`, `PipelineConfig` env loading). The rest of the codebase has substantial untested surface:

| Module | Lines | Coverage |
|---|---:|---:|
| `pipelines/deploy.py` | 61 | 0% — CLI entry point |
| `pipelines/deploy_pipeline/deployer.py` | 48 | 0% — Deploy orchestrator |
| `pipelines/deploy_pipeline/deploy_terraform.py` | 56 | 0% — `terraform init/plan/apply` shellout |
| `pipelines/deploy_pipeline/deploy_monaco.py` | 52 | 0% — `monaco deploy` shellout |
| `pipelines/deploy_pipeline/format_detector.py` | 44 | 0% — Auto-detect terraform vs monaco |
| `pipelines/deploy_pipeline/results_analyzer.py` | 31 | 0% — Post-deploy count comparison |
| `pipelines/export.py` | ~60 | 0% (estimated) — CLI entry point |
| `pipelines/export_pipeline/exporter.py` | ~50 | 0% (estimated) — Export orchestrator |
| `pipelines/export_pipeline/format_terraform.py` | ~80 | 0% (estimated) — `.tf.json` generator |
| `pipelines/export_pipeline/format_monaco.py` | ~80 | 0% (estimated) — Monaco v2 generator |
| `pipelines/export_pipeline/reconciliation.py` | ~40 | 0% (estimated) — Export-vs-tenant compare |
| `pipelines/export_pipeline/topology.py` | ~60 | 0% (estimated) — Dependency graph |
| `pipelines/core/dt_client.py::export_all` | ~50 | 0% (the loop; auth routing is 100%) |
| `pipelines/core/logging_setup.py` | 19 | 0% — Small file, easy |
| `scripts/validate_citation_urls.py` | ~120 | 0% — Phase 04 script |

**Overall test coverage today: ~25-30%.** Goal: bring overall to ≥ 60% with focus on the high-risk paths (deploy_pipeline orchestration, format detection, reconciliation).

## Tasks

- [ ] **`tests/test_format_detector.py`** — pure-function module (reads files / paths, returns enum). Cover: detects terraform from `.tf.json` files, detects monaco from `manifest.yaml`, returns `unknown` for empty or mixed dirs.
- [ ] **`tests/test_results_analyzer.py`** — small module computing before/after deltas. Cover: equal counts, growth, shrinkage, mixed (some up, some down), zero-baseline.
- [ ] **`tests/test_logging_setup.py`** — small file, mostly format strings. Cover: logger name, handler attached once (not duplicated on re-call), format includes timestamp and level.
- [ ] **`tests/test_format_terraform.py`** — JSON generator. Cover: generates valid JSON, includes provider block, variable definitions, resource blocks per config type; handles empty input; respects type → terraform-resource-name mapping in `types.py`.
- [ ] **`tests/test_format_monaco.py`** — Monaco v2 structure generator. Cover: produces `manifest.yaml` + per-type `config.yaml` + JSON payloads; correct directory layout.
- [ ] **`tests/test_reconciliation.py`** — Compares tenant counts vs exported counts. Mock `DynatraceClient.get_counts`; assert missing items list is computed correctly.
- [ ] **`tests/test_topology.py`** — Cross-reference scanner. Cover: detects alerting-profile → management-zone references; computes deployment order by dependency layer.
- [ ] **`tests/test_export_all_loop.py`** — `DynatraceClient.export_all` integration-style test using `tmp_path` + `responses` to mock the Dynatrace API; assert files are written, names sanitized, failure list populated on partial failure.
- [ ] **`tests/test_deployer.py`** — Top-level Deploy orchestrator. Mock `format_detector`, `deploy_terraform`, `deploy_monaco`. Assert the right deployer is called based on detected format; dry-run flag is propagated.
- [ ] **`tests/test_deploy_terraform.py`** — Mock `subprocess.run` for `terraform init/plan/apply`. Assert correct argument lists; assert env vars propagated; assert error handling on non-zero exit.
- [ ] **`tests/test_deploy_monaco.py`** — Same pattern for `monaco deploy` shellout.
- [ ] **`tests/test_export_py.py`** — CLI entry; `argparse` smoke + `--list-types` happy path + config loading delegation.
- [ ] **`tests/test_deploy_py.py`** — CLI entry; same shape as export_py.
- [ ] **`tests/test_validate_citation_urls.py`** — Phase 04 script. Cover: placeholder filter regex (positive + negative cases), URL extraction from markdown + Python, file-walk respects SKIP_FILES, report-writing format.

## Acceptance Criteria

- Overall coverage `pipelines/` + `scripts/` ≥ 60% (currently ~25-30%)
- All four high-risk modules ≥ 80%: `format_detector.py`, `results_analyzer.py`, `deployer.py`, `topology.py`
- No coverage regression on Phase 03's auth-routing tests (must stay at 100% on `_auth_header_for_url` etc.)
- CI workflow stays green across the 3.9 / 3.11 / 3.12 matrix
- Mocking discipline: tests don't make real HTTP calls (`responses` library), don't shell out to real `terraform` / `monaco` binaries (`subprocess` mocking), don't touch the real filesystem outside `tmp_path` fixtures

## Decisions Made This Phase

- 2026-05-12 — Phase scoped to `pipelines/` and `scripts/` test coverage; deliberately NOT addressing other deferred items (B Settings 2.0 migration for management-zones, D expanded config-type coverage). Reason: testing is foundational discipline; deferring it risks Phase 06+ work compounding on untested code. B and D become Phase 06 / 07 candidates after coverage is in place.
- 2026-05-12 — Coverage target 60% overall (not 80% or 90%). Reason: pragmatic ceiling for a project of this size; the highest-risk modules get to 80%, the lower-risk CLI-shim modules can stay at lower coverage. Going higher than 60% overall means writing tests for trivial CLI delegation code where the value is low.
- 2026-05-12 — Mocking discipline: `responses` for HTTP (already in dev deps), `unittest.mock` for `subprocess` (stdlib), `tmp_path` pytest fixture for filesystem. No new dev dependencies introduced.
