#!/usr/bin/env python3
"""Tests for runtime/lib/file_handoff.py."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.file_handoff import validate_handoff_inputs, resolve_handoff_rules


@pytest.fixture
def workflow_dir(tmp_path):
    """Create a mock workflow directory with step outputs."""
    # relax step output
    (tmp_path / "relax" / "output").mkdir(parents=True)
    (tmp_path / "relax" / "output" / "CONTCAR").write_text("relaxed structure")
    (tmp_path / "relax" / "output" / "OUTCAR").write_text("outcar data")

    # scf step output
    (tmp_path / "scf" / "output").mkdir(parents=True)
    (tmp_path / "scf" / "output" / "WAVECAR").write_text("wavecar data")
    (tmp_path / "scf" / "output" / "CHGCAR").write_text("chgcar data")

    # bands step (destination, no output yet)
    (tmp_path / "bands").mkdir(parents=True)

    return tmp_path


class TestValidateHandoffInputs:
    def test_all_sources_exist(self, workflow_dir):
        """validate returns valid=True when all source files exist."""
        rules = [
            {"source": "relax/output/CONTCAR", "dest": "scf/POSCAR"},
            {"source": "scf/output/WAVECAR", "dest": "bands/WAVECAR"},
        ]
        result = validate_handoff_inputs(rules, str(workflow_dir))
        assert result["valid"] is True
        assert len(result["missing"]) == 0

    def test_missing_source(self, workflow_dir):
        """validate returns valid=False when a source file is missing."""
        rules = [
            {"source": "relax/output/CONTCAR", "dest": "scf/POSCAR"},
            {"source": "nonexistent/file", "dest": "bands/FILE"},
        ]
        result = validate_handoff_inputs(rules, str(workflow_dir))
        assert result["valid"] is False
        assert len(result["missing"]) == 1
        assert "nonexistent/file" in result["missing"][0]

    def test_missing_key_in_rule(self, workflow_dir):
        """validate reports error for rules missing source or dest."""
        rules = [
            {"source": "relax/output/CONTCAR"},  # missing dest
        ]
        result = validate_handoff_inputs(rules, str(workflow_dir))
        assert result["valid"] is False
        assert len(result["errors"]) == 1

    def test_empty_rules(self, workflow_dir):
        """validate handles empty rules list."""
        result = validate_handoff_inputs([], str(workflow_dir))
        assert result["valid"] is True


class TestResolveHandoffRules:
    def test_single_copy(self, workflow_dir):
        """resolve copies a single file correctly."""
        rules = [
            {"source": "relax/output/CONTCAR", "dest": "scf/POSCAR"},
        ]
        result = resolve_handoff_rules(rules, str(workflow_dir))
        assert len(result["errors"]) == 0
        assert len(result["copied"]) == 1
        assert (workflow_dir / "scf" / "POSCAR").exists()
        assert (workflow_dir / "scf" / "POSCAR").read_text() == "relaxed structure"

    def test_multiple_copies(self, workflow_dir):
        """resolve handles multiple handoff rules."""
        rules = [
            {"source": "relax/output/CONTCAR", "dest": "scf/POSCAR"},
            {"source": "relax/output/CONTCAR", "dest": "bands/POSCAR"},
            {"source": "scf/output/WAVECAR", "dest": "bands/WAVECAR"},
            {"source": "scf/output/CHGCAR", "dest": "bands/CHGCAR"},
        ]
        result = resolve_handoff_rules(rules, str(workflow_dir))
        assert len(result["errors"]) == 0
        assert len(result["copied"]) == 4
        assert (workflow_dir / "bands" / "POSCAR").read_text() == "relaxed structure"
        assert (workflow_dir / "bands" / "WAVECAR").read_text() == "wavecar data"
        assert (workflow_dir / "bands" / "CHGCAR").read_text() == "chgcar data"

    def test_creates_destination_directory(self, workflow_dir):
        """resolve creates intermediate directories if needed."""
        rules = [
            {"source": "relax/output/CONTCAR", "dest": "deep/nested/dir/POSCAR"},
        ]
        result = resolve_handoff_rules(rules, str(workflow_dir))
        assert len(result["errors"]) == 0
        assert (workflow_dir / "deep" / "nested" / "dir" / "POSCAR").exists()

    def test_missing_source_reported_as_error(self, workflow_dir):
        """resolve reports missing source files as errors."""
        rules = [
            {"source": "nonexistent/file", "dest": "bands/FILE"},
        ]
        result = resolve_handoff_rules(rules, str(workflow_dir))
        assert len(result["errors"]) == 1
        assert len(result["copied"]) == 0

    def test_missing_key_reported_as_error(self, workflow_dir):
        """resolve reports rules with missing keys as errors."""
        rules = [
            {"source": "relax/output/CONTCAR"},  # missing dest
        ]
        result = resolve_handoff_rules(rules, str(workflow_dir))
        assert len(result["errors"]) == 1

    def test_empty_rules(self, workflow_dir):
        """resolve handles empty rules list."""
        result = resolve_handoff_rules([], str(workflow_dir))
        assert result["copied"] == []
        assert result["errors"] == []

    def test_same_file_multiple_destinations(self, workflow_dir):
        """resolve can copy one source to multiple destinations."""
        rules = [
            {"source": "relax/output/CONTCAR", "dest": "step1/POSCAR"},
            {"source": "relax/output/CONTCAR", "dest": "step2/POSCAR"},
            {"source": "relax/output/CONTCAR", "dest": "step3/POSCAR"},
        ]
        result = resolve_handoff_rules(rules, str(workflow_dir))
        assert len(result["copied"]) == 3
        for step in ["step1", "step2", "step3"]:
            assert (workflow_dir / step / "POSCAR").read_text() == "relaxed structure"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
