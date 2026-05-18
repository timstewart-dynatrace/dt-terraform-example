# Citation Status

> **Tool:** `scripts/validate_citation_urls.py`
> **Scope:** every `https://...` URL found in `*.md`, `.claude/**`, `docs/**`, `pipelines/**`, `tests/**`, `scripts/**`.
> **Filter:** placeholder URLs (variables, example domains, all-caps placeholders) excluded.

## Summary

- **Total unique URLs checked:** 27
- **Live (2xx):** 26
- **Redirected (3xx):** 0
- **404:** 0
- **Other 4xx / 5xx:** 1
- **Timeouts:** 0
- **Unreachable:** 0

## Other 4xx / 5xx

- `https://community.dynatrace.com/` (HTTP 403)
  - docs/TROUBLESHOOTING.md

## All URLs

| Status | URL | Sources |
|---:|---|---|
| ✓ | `https://abc.live.dynatrace.com` | .claude/rules/python.md |
| 403 | `https://community.dynatrace.com/` | docs/TROUBLESHOOTING.md |
| ✓ | `https://def67890.live.dynatrace.com` | .claude/rules/development.md |
| ✓ | `https://docs.dynatrace.com/docs/deliver/configuration-as-code` | docs/GETTING_STARTED.md |
| ✓ | `https://docs.dynatrace.com/docs/manage/identity-access-management/access-tokens-and-oauth-clients/platform-tokens` | .claude/rules/reference-currency.md<br>tests/test_auth_header.py |
| ✓ | `https://from-env.live.dynatrace.com` | tests/test_config_loader.py |
| ✓ | `https://from-yaml.live.dynatrace.com` | tests/test_config_loader.py |
| ✓ | `https://github.com/Dynatrace/dynatrace-configuration-as-code` | README.md |
| ✓ | `https://github.com/dynatrace-oss/terraform-provider-dynatrace/releases` | .claude/rules/reference-currency.md |
| ✓ | `https://github.com/dynatrace-oss/terraform-provider-dynatrace/releases/tag/v1.88.0` | .claude/rules/reference-currency.md<br>CHANGELOG.md<br>README.md<br>pipelines/core/dt_client.py<br>tests/test_auth_routing.py |
| ✓ | `https://github.com/timstewart-dynatrace/dt-terraform-example/issues` | docs/TROUBLESHOOTING.md |
| ✓ | `https://keepachangelog.com/en/1.0.0/` | .claude/rules/core.md<br>CHANGELOG.md |
| ✓ | `https://prod-source.live.dynatrace.com` | docs/ADVANCED.md |
| ✓ | `https://prod-target.live.dynatrace.com` | docs/ADVANCED.md |
| ✓ | `https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest` | .claude/rules/reference-currency.md<br>README.md<br>docs/GETTING_STARTED.md<br>docs/TROUBLESHOOTING.md |
| ✓ | `https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest/docs/resources/iam_group` | .claude/DECISIONS.md |
| ✓ | `https://semver.org/` | .claude/rules/core.md |
| ✓ | `https://semver.org/spec/v2.0.0.html` | CHANGELOG.md |
| ✓ | `https://source.live.dynatrace.com` | scripts/migrate.py |
| ✓ | `https://src.live.dynatrace.com` | tests/test_config_loader.py |
| ✓ | `https://target.live.dynatrace.com` | pipelines/deploy.py<br>scripts/migrate.py |
| ✓ | `https://tenant.live.dynatrace.com` | pipelines/export.py |
| ✓ | `https://tgt.live.dynatrace.com` | tests/test_config_loader.py |
| ✓ | `https://www.dynatrace.com/support/help/dynatrace-api` | README.md<br>docs/GETTING_STARTED.md<br>docs/TROUBLESHOOTING.md |
| ✓ | `https://x.live.dynatrace.com` | tests/test_tenant_config.py |
| ✓ | `https://yaml-tgt.live.dynatrace.com` | tests/test_config_loader.py |
| ✓ | `https://your-environment-id.live.dynatrace.com` | docs/TROUBLESHOOTING.md |
