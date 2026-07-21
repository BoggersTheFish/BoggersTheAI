"""
Tests for tools/check_docs.py canonical repository metadata rules.
"""

from __future__ import annotations

from pathlib import Path

from tools import check_docs


def test_canonical_url_constants():
    assert check_docs.CANONICAL_REPO == "BoggersTheFish/thinking-system"
    assert (
        check_docs.CANONICAL_URL == "https://github.com/BoggersTheFish/thinking-system"
    )
    assert "BoggersTheAI" in check_docs.FORMER_URL


def test_repo_readme_has_canonical_url():
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert check_docs.CANONICAL_URL in readme or check_docs.CANONICAL_REPO in readme
    # Badge must not point at former active actions path
    assert "BoggersTheAI/actions/workflows" not in readme


def test_citation_points_at_thinking_system():
    root = Path(__file__).resolve().parents[1]
    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    assert check_docs.CANONICAL_URL in citation
    assert (
        'repository-code: "https://github.com/BoggersTheFish/BoggersTheAI"'
        not in citation
    )


def test_stale_active_patterns_flag_old_clone(tmp_path: Path, monkeypatch):
    """Synthetic README with old clone URL must fail stale-link check."""
    (tmp_path / "README.md").write_text(
        "git clone https://github.com/BoggersTheFish/BoggersTheAI.git\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_docs, "ROOT_DIR", tmp_path)
    errors = check_docs.check_stale_active_links()
    assert any("stale active" in e for e in errors)


def test_historical_former_remote_line_not_flagged(tmp_path: Path, monkeypatch):
    """Former remote documented as historical is allowed."""
    (tmp_path / "README.md").write_text(
        f"| **Current remote** | `{check_docs.CANONICAL_REPO}` |\n"
        f"| **Former remote** | `BoggersTheFish/BoggersTheAI` (renamed) |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_docs, "ROOT_DIR", tmp_path)
    errors = check_docs.check_stale_active_links()
    assert errors == []


def test_check_docs_main_passes_on_real_repo():
    assert check_docs.main() == 0
