"""Ensure historical release notes match their corresponding Git tags.

Per AGENTS.md §2.5: "Historical release notes remain tied to their tags
and must not be rewritten with the current main-branch version."
"""
from __future__ import annotations
import hashlib
import subprocess
from pathlib import Path
import pytest

# Git root relative to this test file
_PROJECT = Path(__file__).resolve().parents[2]


def _git_show_file(ref: str, path: str) -> str:
    """Return file contents from a specific git ref."""
    return subprocess.check_output(
        ["git", "show", f"{ref}:{path}"],
        cwd=str(_PROJECT), text=True, encoding="utf-8",
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestReleaseNoteTagIntegrity:
    """Historical release notes must match their tag content byte-for-byte."""

    RELEASE_NOTES = [
        ("v0.5.0-rc1", "docs/releases/v0.5.0-rc1.md"),
    ]

    @pytest.mark.parametrize("tag,path", RELEASE_NOTES)
    def test_release_note_matches_tag(self, tag, path):
        """Release note file content must be identical to the tagged version."""
        tagged_content = _git_show_file(tag, path)
        current_content = (_PROJECT / path).read_text(encoding="utf-8")

        # Normalise line endings: Windows CRLF ↔ LF
        tagged_normalised = tagged_content.replace("\r\n", "\n")
        current_normalised = current_content.replace("\r\n", "\n")

        assert tagged_normalised == current_normalised, (
            f"{path} differs from tag {tag}. "
            "Per AGENTS.md, historical release notes must not be rewritten "
            "with current main-branch content. "
            "Update the current version's release note, PROJECT_STATE.md, "
            "or CAPABILITY_MATRIX.md instead.\n\n"
            f"Tag SHA256: {_sha256(tagged_normalised)}\n"
            f"File SHA256: {_sha256(current_normalised)}"
        )
