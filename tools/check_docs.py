#!/usr/bin/env python3
"""
Thinking System Documentation Link & Consistency Checker.

Checks:
1. Required documentation files exist.
2. Canonical active repository URL is present in key metadata files.
3. Stale *active* links to the former GitHub path are not left as
   canonical clone/badge/citation URLs.

Intentional historical mentions of ``BoggersTheFish/BoggersTheAI`` (former
name, provenance tables, ADRs) are allowed when they are not the sole
canonical repository URL for README/CITATION badges and project URLs.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

CANONICAL_REPO = "BoggersTheFish/thinking-system"
CANONICAL_URL = f"https://github.com/{CANONICAL_REPO}"
FORMER_URL = "https://github.com/BoggersTheFish/BoggersTheAI"

REQUIRED_DOCS = [
    "README.md",
    "LICENSE",
    "CITATION.cff",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "GOVERNANCE.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "AGENTS.md",
    "docs/migration/baseline.md",
    "docs/lineage/repository-inventory.md",
    "docs/migration/import-ledger.md",
    "docs/claims-and-evidence/claim-ledger.md",
]

# Files where the *active* GitHub clone/badge/citation URL must be canonical.
CANONICAL_URL_REQUIRED_IN = (
    "README.md",
    "CITATION.cff",
)

# Patterns that indicate a stale *active* link (not historical prose).
STALE_ACTIVE_PATTERNS = (
    re.compile(
        r"https://github\.com/BoggersTheFish/BoggersTheAI/actions/",
        re.MULTILINE,
    ),
    re.compile(
        r"git clone https://github\.com/BoggersTheFish/BoggersTheAI\.git",
        re.MULTILINE,
    ),
    re.compile(
        r'repository-code:\s*"https://github\.com/BoggersTheFish/BoggersTheAI"',
        re.MULTILINE,
    ),
    re.compile(
        r'url:\s*"https://github\.com/BoggersTheFish/BoggersTheAI"',
        re.MULTILINE,
    ),
    re.compile(
        r"\*\*Current remote\*\*.*BoggersTheFish/BoggersTheAI",
        re.MULTILINE,
    ),
    re.compile(
        r"\*\*Planned remote\*\*.*thinking-system.*rename not",
        re.MULTILINE | re.IGNORECASE,
    ),
)


def check_required_files() -> list[str]:
    missing = []
    for doc in REQUIRED_DOCS:
        if not (ROOT_DIR / doc).exists():
            missing.append(doc)
    if missing:
        return [f"Missing required documentation files: {missing}"]
    return []


def check_canonical_urls_present() -> list[str]:
    errors: list[str] = []
    for rel in CANONICAL_URL_REQUIRED_IN:
        text = (ROOT_DIR / rel).read_text(encoding="utf-8", errors="ignore")
        if CANONICAL_URL not in text and CANONICAL_REPO not in text:
            errors.append(
                f"{rel}: missing canonical repository reference "
                f"({CANONICAL_URL} or {CANONICAL_REPO})"
            )
    return errors


def check_stale_active_links() -> list[str]:
    """Scan key files for patterns that must not remain after rename."""
    errors: list[str] = []
    scan_paths = [
        ROOT_DIR / "README.md",
        ROOT_DIR / "CITATION.cff",
        ROOT_DIR / "CONTRIBUTING.md",
        ROOT_DIR / "SECURITY.md",
        ROOT_DIR / "GOVERNANCE.md",
        ROOT_DIR / "docs" / "migration" / "final-report.md",
        ROOT_DIR / "docs" / "migration" / "github-profile-plan.md",
        ROOT_DIR / "docs" / "lineage" / "repository-inventory.md",
        ROOT_DIR / "docs" / "templates" / "ARCHIVE_README.md",
    ]
    for path in scan_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(ROOT_DIR).as_posix()
        for pat in STALE_ACTIVE_PATTERNS:
            if pat.search(text):
                errors.append(
                    f"{rel}: stale active former-repository link pattern "
                    f"matched /{pat.pattern}/ — use {CANONICAL_URL}"
                )
    return errors


def main() -> int:
    print("Checking required documentation files...")
    print(f"Canonical repository: {CANONICAL_URL}")
    all_errors: list[str] = []
    all_errors.extend(check_required_files())
    all_errors.extend(check_canonical_urls_present())
    all_errors.extend(check_stale_active_links())

    if all_errors:
        print(f"FAILED: {len(all_errors)} documentation consistency issue(s):")
        for e in all_errors:
            print(" -", e)
        return 1

    print("SUCCESS: All required documentation files are present.")
    print("SUCCESS: Canonical repository metadata checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
