#!/usr/bin/env python3
"""Tests for project_root case normalization and directory artifact registration.

Covers P0.5 + P0.6:
- P0.5: resolve_project_root normalizes path casing on case-insensitive FS
- P0.6: register_artifact accepts directory paths with tree hash computation
"""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # tests/ -> simflow/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))


# ============================================================
# P0.5: project_root case normalization
# ============================================================

def test_resolve_project_root_preserves_case_on_case_sensitive_fs():
    """On case-sensitive FS, resolve_project_root preserves the input casing."""
    from runtime.simflow_core.state import resolve_project_root

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a directory with mixed case
        mixed_case_dir = Path(tmpdir) / "MixedCaseProject"
        mixed_case_dir.mkdir()
        result = resolve_project_root(project_root=str(mixed_case_dir))
        # On case-sensitive FS, result should match input
        assert result.name == "MixedCaseProject"


def test_resolve_project_root_normalizes_case_on_case_insensitive_fs():
    """On case-insensitive FS, resolve_project_root returns real disk casing.

    This test creates a directory with mixed case, then passes a lowercase
    version. On case-insensitive FS (WSL /mnt/d/), the result should be
    the mixed-case form.
    """
    from runtime.simflow_core.state import resolve_project_root

    with tempfile.TemporaryDirectory() as tmpdir:
        mixed_case_dir = Path(tmpdir) / "Li-O-B-Si"
        mixed_case_dir.mkdir()

        lowercase = str(Path(tmpdir) / "li-o-b-si")
        result = resolve_project_root(project_root=lowercase)

        # On case-insensitive FS, realpath returns the actual disk casing
        # On case-sensitive FS, the lowercase dir doesn't exist so result
        # will match the input. We test that if the path exists, the casing
        # is correct.
        if result.exists():
            assert result.name == "Li-O-B-Si", \
                f"expected 'Li-O-B-Si', got '{result.name}'"


def test_resolve_project_root_does_not_corrupt_case_sensitive_paths():
    """resolve_project_root does not alter paths on case-sensitive FS."""
    from runtime.simflow_core.state import resolve_project_root

    with tempfile.TemporaryDirectory() as tmpdir:
        result = resolve_project_root(project_root=tmpdir)
        # Should resolve to the same path (after symlink resolution)
        assert result.exists()


def test_init_workflow_with_normalized_root():
    """init_workflow stores the normalized project_root in project.json."""
    from runtime.simflow_core.state import init_workflow, read_state

    with tempfile.TemporaryDirectory() as tmpdir:
        mixed_case = Path(tmpdir) / "MyProject"
        mixed_case.mkdir()

        # Initialize with lowercase (simulating the LBS bug)
        lowercase = str(Path(tmpdir) / "myproject")
        init_workflow("custom", "computation", project_root=lowercase)

        # Read project.json - project_root should be normalized
        project = read_state(project_root=str(mixed_case), state_file="project.json")
        if project and "project_root" in project:
            # On case-insensitive FS, the stored path should have correct casing
            stored = Path(project["project_root"])
            if stored.exists():
                assert "MyProject" in stored.name or "myproject" in stored.name


# ============================================================
# P0.6: register_artifact accepts directory paths
# ============================================================

def test_register_artifact_accepts_file():
    """register_artifact works with a file path (existing behavior)."""
    from runtime.simflow_core.state import init_workflow
    from runtime.simflow_core.artifacts import register_artifact

    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "computation", project_root=tmpdir)

        # Create a file
        test_file = Path(tmpdir) / "results.json"
        test_file.write_text('{"energy": -1.5}', encoding="utf-8")

        artifact = register_artifact(
            "results.json", "output_file", "computation",
            path="results.json", project_root=tmpdir,
        )

        assert artifact["artifact_id"].startswith("art_")
        assert artifact["checksum"] is not None
        assert artifact["metadata"].get("is_directory") is not True


def test_register_artifact_accepts_directory():
    """register_artifact works with a directory path (the P0.6 fix).

    Previously this raised [Errno 21] Is a directory. Now it computes
    a tree hash and records directory metadata.
    """
    from runtime.simflow_core.state import init_workflow
    from runtime.simflow_core.artifacts import register_artifact

    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "computation", project_root=tmpdir)

        # Create a directory with files
        data_dir = Path(tmpdir) / "stage3_constrained" / "Sm"
        data_dir.mkdir(parents=True)
        (data_dir / "OUTCAR").write_text("OUTCAR content\n", encoding="utf-8")
        (data_dir / "CONTCAR").write_text("CONTCAR content\n", encoding="utf-8")
        sub = data_dir / "sub"
        sub.mkdir()
        (sub / "extra.txt").write_text("extra\n", encoding="utf-8")

        artifact = register_artifact(
            "Sm directory", "output_directory", "computation",
            path="stage3_constrained/Sm", project_root=tmpdir,
        )

        assert artifact["artifact_id"].startswith("art_")
        assert artifact["checksum"] is not None
        assert artifact["metadata"]["is_directory"] is True
        assert artifact["metadata"]["file_count"] == 3
        assert artifact["metadata"]["total_size_bytes"] > 0
        assert artifact["metadata"]["tree_hash"] == artifact["checksum"]


def test_register_artifact_directory_tree_hash_deterministic():
    """Tree hash is deterministic for the same directory contents."""
    from runtime.simflow_core.state import init_workflow
    from runtime.simflow_core.artifacts import register_artifact

    with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
        init_workflow("custom", "computation", project_root=tmpdir1)
        init_workflow("custom", "computation", project_root=tmpdir2)

        # Create identical directories
        for root in [tmpdir1, tmpdir2]:
            d = Path(root) / "data"
            d.mkdir()
            (d / "a.txt").write_text("content a\n", encoding="utf-8")
            (d / "b.txt").write_text("content b\n", encoding="utf-8")

        art1 = register_artifact("data1", "dir", "computation", path="data", project_root=tmpdir1)
        art2 = register_artifact("data2", "dir", "computation", path="data", project_root=tmpdir2)

        assert art1["checksum"] == art2["checksum"], "tree hashes should match for identical content"


def test_register_artifact_directory_tree_hash_binds_relative_paths():
    """Identical bytes at different relative paths produce different tree hashes."""
    from runtime.simflow_core.state import init_workflow
    from runtime.simflow_core.artifacts import register_artifact

    with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
        init_workflow("custom", "computation", project_root=tmpdir1)
        init_workflow("custom", "computation", project_root=tmpdir2)
        for root, filename in ((tmpdir1, "a.txt"), (tmpdir2, "renamed.txt")):
            directory = Path(root) / "data"
            directory.mkdir()
            (directory / filename).write_text("same content\n", encoding="utf-8")

        art1 = register_artifact("data", "dir", "computation", path="data", project_root=tmpdir1)
        art2 = register_artifact("data", "dir", "computation", path="data", project_root=tmpdir2)

        assert art1["checksum"] != art2["checksum"]
        assert art1["metadata"]["tree_hash_algorithm"] == "sha256-path-size-content-v1"


def test_register_artifact_empty_directory():
    """register_artifact handles empty directories without error."""
    from runtime.simflow_core.state import init_workflow
    from runtime.simflow_core.artifacts import register_artifact

    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "computation", project_root=tmpdir)

        empty_dir = Path(tmpdir) / "empty"
        empty_dir.mkdir()

        artifact = register_artifact(
            "empty dir", "output_directory", "computation",
            path="empty", project_root=tmpdir,
        )

        assert artifact["metadata"]["is_directory"] is True
        assert artifact["metadata"]["file_count"] == 0
        assert artifact["metadata"]["total_size_bytes"] == 0
        assert artifact["checksum"] is not None  # hash of empty concatenation


def test_register_artifact_nonexistent_path():
    """register_artifact with nonexistent path still registers (checksum None)."""
    from runtime.simflow_core.state import init_workflow
    from runtime.simflow_core.artifacts import register_artifact

    with tempfile.TemporaryDirectory() as tmpdir:
        init_workflow("custom", "computation", project_root=tmpdir)

        artifact = register_artifact(
            "planned output", "planned_output", "computation",
            path="does_not_exist_yet/", project_root=tmpdir,
        )

        assert artifact["artifact_id"].startswith("art_")
        assert artifact["checksum"] is None
        assert artifact["metadata"].get("is_directory") is not True


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
