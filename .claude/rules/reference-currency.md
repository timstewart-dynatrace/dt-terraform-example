# Reference Currency Rule

When this project cites a URL — in README, DECISIONS, CHANGELOG, code docstrings, or `.claude/` files — that citation is a claim about the source at the moment it was written. The Dynatrace landscape shifts faster than most software-engineering domains (provider releases every 2–3 weeks; auth-model changes mid-version; resource renames between minor versions). A documented currency discipline keeps the citations from rotting.

This rule has **two directives** — one applied per-edit, one applied periodically.

---

## Directive 1 — Next-touch reference standardization

**When editing any file that contains cited URLs**, follow these rules before commit:

- **Title format:** `[Title (publisher)](URL)`. The publisher tag in parentheses conveys source quality without a separate tier label. Examples: `[Platform tokens (DT docs)](URL)`, `[v1.88.0 release notes (Dynatrace GitHub)](URL)`.
- **No marketing taglines** in link titles. Quote the document's actual title.
- **Cite the source page**, not a docs-assistant summary or LLM-synthesized answer. If a docs-bot tool surfaced a URL, fetch that URL and confirm the quoted statement is there.
- **No internal-rule links from user-facing docs.** Don't cite `.claude/rules/...` from README — those files are agent configuration, not user documentation.
- **Trailing description on a link** only when the description is itself load-bearing (a direct quote that anchors a claim, a version-specific note, a failure-mode caveat). Don't add description that just restates the link's title.
- **Direct quotes:** wrap in italic single quotes — `*"The OAuth functionality has been removed..."*` — so the rendered output makes it visible that the words are the source's, not ours.

**Apply only on next-touch — no retrofit sweep.** The corpus converges incrementally; a one-shot rewrite of every existing reference is not justified by the maintenance cost.

---

## Directive 2 — Deep content verification (periodic)

URL liveness — does the URL still return 200? — catches the most common form of drift (broken links). It does not catch the harder form: URL still returns 200 but the page now describes a different feature, or the quoted statement is no longer present. Triggers and tools:

### URL liveness check

Run `python3 scripts/validate_citation_urls.py` to walk the project's documentation surfaces and check every `https://...` URL. Output: `docs/citation-status.md` with totals + per-source breakdown + 404 list. Exit code 0 if clean, 1 if any 404s — suitable for CI gating once the baseline is clean.

**When to run:**

- **Before opening a PR that touches citations** — confirm no new URLs are broken.
- **Monthly** as a routine maintenance task — typically catches Dynatrace docs reorganizations.
- **After major Dynatrace provider releases** (every 2–3 weeks; check the [provider releases page](https://github.com/dynatrace-oss/terraform-provider-dynatrace/releases)) — re-verify the v1.88.0 boundary list against the latest release notes; the boundary has continued to shift through v1.88–v1.96.

### Content drift check (manual)

For the most load-bearing citations (the v1.88.0 release-note quote in `dt_client.py`; the Platform Tokens documentation page cited in README), spot-check the cited statement is still present on the source page when the page might have been edited.

**When to spot-check:**

- **When the latest Dynatrace Terraform provider release** explicitly mentions auth-routing changes — re-read the v1.88.0 release notes AND the latest release notes; reconcile.
- **When a customer or operator reports a 401 against an endpoint the project routes via Platform Token** — that's the empirical signal that the boundary may have shifted.
- **Quarterly** for the README's "Getting API Tokens" section.

---

## Most load-bearing citations

These are the citations whose drift would actually break the project. Verify them carefully:

| Citation | Where | Why it matters |
|---|---|---|
| [v1.88.0 release notes (Dynatrace GitHub)](https://github.com/dynatrace-oss/terraform-provider-dynatrace/releases/tag/v1.88.0) — *"The OAuth functionality has been removed for the following resources, which previously relied on the `environment-api:*` scopes."* | `pipelines/core/dt_client.py` module docstring; README "Getting API Tokens" | Defines the auth-routing boundary. If Dynatrace shifts the boundary in a future provider release, our `_CLASSIC_API_TOKEN_URL_PATTERNS` list goes stale. |
| [Platform tokens (DT docs)](https://docs.dynatrace.com/docs/manage/identity-access-management/access-tokens-and-oauth-clients/platform-tokens) | README; `dt_client.py` docstring | Defines the `Authorization: Bearer` header format for Platform Tokens. |
| [dynatrace-oss/dynatrace provider releases](https://registry.terraform.io/providers/dynatrace-oss/dynatrace/latest) | README | The Terraform-provider-side documentation that downstream Terraform shops will be using; if its layout changes drastically, our README references go stale. |

---

## What this rule deliberately does NOT mandate

- A retroactive sweep of every existing reference in the project. The directive applies on next-touch only — incremental drift correction, not a one-shot rewrite.
- A specific cadence for the URL liveness check beyond "monthly + on PR + after major provider releases". Project size doesn't justify a stricter SLA.
- A separate `references.md` master bibliography. Citations live where they're used (README, DECISIONS, docstrings); a master bibliography would duplicate them and inevitably drift out of sync with the canonical site.
- Content-drift detection beyond manual spot-checks. Automating "the page still says what we quoted" is a much harder problem than URL liveness; the project's small citation surface makes manual checking sustainable.

---

## Source

Adapted from the **Best-Practice-Notebooks-Generator** project's `.claude/rules/workflow.md` § Reference Currency directive. That project has a larger citation surface (446 notebooks across 34 series) and stricter cadence requirements. This rule is the small-codebase version of the same idea.
