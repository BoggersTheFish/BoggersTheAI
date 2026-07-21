#!/usr/bin/env python3
"""
Thinking System Documentation Link & Consistency Checker.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

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
    "docs/claims-and-evidence/claim-ledger.md",
]


def main():
    print("Checking required documentation files...")
    missing = []
    for doc in REQUIRED_DOCS:
        p = ROOT_DIR / doc
        if not p.exists():
            missing.append(doc)

    if missing:
        print(f"FAILED: Missing required documentation files: {missing}")
        sys.exit(1)

    print("SUCCESS: All required documentation files are present.")
    sys.exit(0)


if __name__ == "__main__":
    main()
