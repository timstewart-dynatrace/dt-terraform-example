#!/usr/bin/env python3
"""Validate citation URLs across the project's documentation surfaces.

Walks all .md files in the repo + Python docstrings/comments under
``pipelines/``, extracts every ``https://...`` URL, filters obvious
placeholders, and HEAD-checks each unique URL. Writes a report to
``docs/citation-status.md``.

Exit codes:
- 0 — no 404s among genuine citations
- 1 — at least one 404 (suitable for CI gating once the baseline is clean)

Run from the project root::

    python3 scripts/validate_citation_urls.py

Implements Directive 2 of ``.claude/rules/reference-currency.md``.
"""

from __future__ import annotations

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "docs" / "citation-status.md"

URL_PATTERN = re.compile(r"https://[A-Za-z0-9./_\-?=&%#:+~,@!$*();]+")

# Placeholder patterns — URLs that legitimately appear in examples but
# aren't real citations. Filtered out before HEAD-checking.
PLACEHOLDER_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"your-(source|target|tenant)[-.]"),  # your-tenant. or your-source- in examples
    re.compile(r"<[a-z\-]+>"),                       # angle-bracket placeholders <token>
    re.compile(r"\{[a-z_]+\}"),                      # curly-brace placeholders {tenant-id}
    re.compile(r"abc12345\.live\.dynatrace\.com"),   # tenant ID placeholder in tests
    re.compile(r"^https://(example|sample)\."),       # example.com etc.
    re.compile(r"YOUR_[A-Z_]+"),                      # YOUR_TOKEN etc.
    re.compile(r"^https://?$"),                       # bare protocol fragments
    re.compile(r"^https://\("),                       # regex artefacts like https://(example
)

# Files to skip entirely (e.g. this script, which has regex strings that look like URLs)
SKIP_FILES = {
    "docs/citation-status.md",        # don't re-cite ourselves
    "scripts/validate_citation_urls.py",  # contains regex patterns that look like URLs
}

# File patterns to scan
SCAN_GLOB_PATTERNS = (
    "*.md",
    ".claude/**/*.md",
    "docs/**/*.md",
    "pipelines/**/*.py",
    "tests/**/*.py",
    "scripts/**/*.py",
)

@dataclass
class UrlResult:
    url: str
    status: int  # HTTP status, 0 for unreachable, -1 for timeout
    sources: Set[str] = field(default_factory=set)


def find_files() -> List[Path]:
    files: List[Path] = []
    seen: Set[Path] = set()
    for pattern in SCAN_GLOB_PATTERNS:
        for p in REPO_ROOT.glob(pattern):
            if p.is_file() and p not in seen:
                rel = p.relative_to(REPO_ROOT).as_posix()
                if rel in SKIP_FILES:
                    continue
                files.append(p)
                seen.add(p)
    return sorted(files)


def is_placeholder(url: str) -> bool:
    return any(p.search(url) for p in PLACEHOLDER_PATTERNS)


def extract_urls(path: Path) -> Set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return set()
    raw = set(URL_PATTERN.findall(text))
    # Trim trailing punctuation often captured by greedy regex
    cleaned = set()
    for u in raw:
        while u and u[-1] in ".,;:)]}>'\"":
            u = u[:-1]
        if u and not is_placeholder(u):
            cleaned.add(u)
    return cleaned


def check_url(url: str, timeout: float = 10.0) -> int:
    """HEAD-check a URL. Falls back to GET if HEAD returns 405 (some servers
    don't honour HEAD). Returns the final HTTP status code, 0 if unreachable,
    -1 if timeout."""
    try:
        resp = requests.head(url, allow_redirects=True, timeout=timeout,
                             headers={"User-Agent": "dt-terraform-example/citation-check"})
        if resp.status_code in (405, 403):
            # Some servers reject HEAD; retry with GET
            resp = requests.get(url, allow_redirects=True, timeout=timeout, stream=True,
                                headers={"User-Agent": "dt-terraform-example/citation-check"})
            resp.close()
        return resp.status_code
    except requests.Timeout:
        return -1
    except requests.RequestException:
        return 0


def collect_citations() -> Dict[str, Set[str]]:
    """Map URL → set of source files that cite it."""
    citations: Dict[str, Set[str]] = {}
    for path in find_files():
        urls = extract_urls(path)
        rel = path.relative_to(REPO_ROOT).as_posix()
        for u in urls:
            citations.setdefault(u, set()).add(rel)
    return citations


def write_report(results: List[UrlResult]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    total = len(results)
    live = sum(1 for r in results if 200 <= r.status < 300)
    redirect = sum(1 for r in results if 300 <= r.status < 400)
    not_found = sum(1 for r in results if r.status == 404)
    other_4xx_5xx = sum(1 for r in results if r.status >= 400 and r.status != 404)
    timeouts = sum(1 for r in results if r.status == -1)
    unreachable = sum(1 for r in results if r.status == 0)

    lines = [
        "# Citation Status",
        "",
        "> **Tool:** `scripts/validate_citation_urls.py`",
        "> **Scope:** every `https://...` URL found in `*.md`, `.claude/**`, `docs/**`, `pipelines/**`, `tests/**`, `scripts/**`.",
        "> **Filter:** placeholder URLs (variables, example domains, all-caps placeholders) excluded.",
        "",
        "## Summary",
        "",
        f"- **Total unique URLs checked:** {total}",
        f"- **Live (2xx):** {live}",
        f"- **Redirected (3xx):** {redirect}",
        f"- **404:** {not_found}",
        f"- **Other 4xx / 5xx:** {other_4xx_5xx}",
        f"- **Timeouts:** {timeouts}",
        f"- **Unreachable:** {unreachable}",
        "",
    ]

    if not_found:
        lines += ["## 404 URLs", ""]
        for r in sorted(results, key=lambda x: x.url):
            if r.status == 404:
                lines.append(f"- `{r.url}`")
                for s in sorted(r.sources):
                    lines.append(f"  - {s}")
        lines.append("")

    if other_4xx_5xx:
        lines += ["## Other 4xx / 5xx", ""]
        for r in sorted(results, key=lambda x: x.url):
            if r.status >= 400 and r.status != 404:
                lines.append(f"- `{r.url}` (HTTP {r.status})")
                for s in sorted(r.sources):
                    lines.append(f"  - {s}")
        lines.append("")

    if timeouts or unreachable:
        lines += ["## Timeouts / Unreachable", ""]
        for r in sorted(results, key=lambda x: x.url):
            if r.status in (-1, 0):
                label = "TIMEOUT" if r.status == -1 else "UNREACHABLE"
                lines.append(f"- `{r.url}` ({label})")
                for s in sorted(r.sources):
                    lines.append(f"  - {s}")
        lines.append("")

    lines += ["## All URLs", "", "| Status | URL | Sources |", "|---:|---|---|"]
    for r in sorted(results, key=lambda x: x.url):
        if r.status == -1:
            badge = "⏱"
        elif r.status == 0:
            badge = "✗"
        elif 200 <= r.status < 300:
            badge = "✓"
        else:
            badge = str(r.status)
        sources_str = "<br>".join(sorted(r.sources))
        lines.append(f"| {badge} | `{r.url}` | {sources_str} |")

    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"Report: {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(f"Summary: {live} live / {not_found} 404 / {timeouts + unreachable} timeout-or-unreachable / {total} total")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Concurrent HEAD checks (default: 8)",
    )
    args = parser.parse_args()

    citations = collect_citations()
    print(f"Collected {len(citations)} unique URLs from {sum(len(s) for s in citations.values())} citation sites")

    results: List[UrlResult] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_to_url = {pool.submit(check_url, u): u for u in citations}
        for i, future in enumerate(as_completed(future_to_url), 1):
            url = future_to_url[future]
            status = future.result()
            results.append(UrlResult(url=url, status=status, sources=citations[url]))
            if i % 10 == 0 or i == len(citations):
                print(f"  {i}/{len(citations)}")

    write_report(results)

    has_404 = any(r.status == 404 for r in results)
    return 1 if has_404 else 0


if __name__ == "__main__":
    sys.exit(main())
