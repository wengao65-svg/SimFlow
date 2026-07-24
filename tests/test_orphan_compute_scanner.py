#!/usr/bin/env python3
"""Tests for orphan_compute_scanner MCP tool.

Covers P2.1:
- Scans project root for compute directories not in jobs.json/artifacts.json
- Detects VASP, CP2K, GPUMD/NEP, LAMMPS marker files
- Flags risky directory names (NoGate, Relaxed, Bypass, SkipGate)
- Writes report to .simflow/reports/orphan_compute_audit.md
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(ROOT / "mcp" / "servers" / "simflow_state"))


def _init(project_root):
    from runtime.simflow_core.state import init_workflow
    return init_workflow("custom", "computation", project_root=project_root)


def _import_scanner():
    from tools.orphan_compute_scanner import execute
    return execute


def test_scanner_finds_orphan_vasp_dir():
    """Scanner finds a VASP directory with OUTCAR not registered in jobs.json."""
    execute = _import_scanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        # Create a fake VASP compute directory
        vasp_dir = Path(tmpdir) / "stage1_vasp_relax" / "La"
        vasp_dir.mkdir(parents=True)
        (vasp_dir / "OUTCAR").write_text("VASP output\n", encoding="utf-8")
        (vasp_dir / "INCAR").write_text("SYSTEM = La\n", encoding="utf-8")

        result = execute({"project_root": tmpdir})

        assert result["status"] == "success"
        assert result["data"]["orphan_count"] >= 1
        orphan_paths = [d["path"] for d in result["data"]["orphan_dirs"]]
        assert any("stage1_vasp_relax" in p for p in orphan_paths)


def test_scanner_finds_orphan_nep_training_dir():
    """Scanner finds a NEP training directory with nep.in + train.xyz."""
    execute = _import_scanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        nep_dir = Path(tmpdir) / "NEP_Training_LBS_2000"
        nep_dir.mkdir(parents=True)
        (nep_dir / "nep.in").write_text("NEP config\n", encoding="utf-8")
        (nep_dir / "train.xyz").write_text("frame data\n", encoding="utf-8")
        (nep_dir / "train.log").write_text("training log\n", encoding="utf-8")

        result = execute({"project_root": tmpdir})

        assert result["status"] == "success"
        orphan_paths = [d["path"] for d in result["data"]["orphan_dirs"]]
        assert any("NEP_Training_LBS_2000" in p for p in orphan_paths)


def test_scanner_finds_orphan_slurm_output():
    """Scanner finds a directory with slurm-*.out."""
    execute = _import_scanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        slurm_dir = Path(tmpdir) / "NEP_Finetune"
        slurm_dir.mkdir(parents=True)
        (slurm_dir / "slurm-1264145.out").write_text("SLURM output\n", encoding="utf-8")

        result = execute({"project_root": tmpdir})

        assert result["status"] == "success"
        orphan_paths = [d["path"] for d in result["data"]["orphan_dirs"]]
        assert any("NEP_Finetune" in p for p in orphan_paths)


def test_scanner_flags_risky_directory_names():
    """Scanner flags directories with NoGate/Relaxed/Bypass/SkipGate patterns."""
    execute = _import_scanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        risky_dir = Path(tmpdir) / "Reproduce_arXiv_NEP2120_Relaxed_NoHighTGate"
        risky_dir.mkdir(parents=True)
        (risky_dir / "gate_decision.json").write_text("{}", encoding="utf-8")

        result = execute({"project_root": tmpdir})

        assert result["status"] == "success"
        assert result["data"]["risky_count"] >= 1
        risky_paths = [d["path"] for d in result["data"]["risky_dirs"]]
        assert any("NoHighTGate" in p or "Relaxed" in p for p in risky_paths)


def test_scanner_skips_registered_dirs():
    """Scanner does not flag directories registered as artifacts."""
    execute = _import_scanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        vasp_dir = Path(tmpdir) / "registered_vasp"
        vasp_dir.mkdir(parents=True)
        (vasp_dir / "OUTCAR").write_text("VASP output\n", encoding="utf-8")

        # Register the directory as an artifact
        from runtime.simflow_core.artifacts import register_artifact
        register_artifact(
            "registered_vasp", "output_directory", "computation",
            path="registered_vasp", project_root=tmpdir,
        )

        result = execute({"project_root": tmpdir})

        assert result["status"] == "success"
        orphan_paths = [d["path"] for d in result["data"]["orphan_dirs"]]
        assert "registered_vasp" not in orphan_paths


def test_scanner_skips_simflow_dirs():
    """Scanner does not scan .simflow, .git, __pycache__ directories."""
    execute = _import_scanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        # .simflow should be skipped
        result = execute({"project_root": tmpdir})

        assert result["status"] == "success"
        orphan_paths = [d["path"] for d in result["data"]["orphan_dirs"]]
        assert not any(".simflow" in p for p in orphan_paths)


def test_scanner_writes_report_file():
    """Scanner writes orphan_compute_audit.md report."""
    execute = _import_scanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        vasp_dir = Path(tmpdir) / "stage1_vasp_relax"
        vasp_dir.mkdir(parents=True)
        (vasp_dir / "OUTCAR").write_text("output\n", encoding="utf-8")

        execute({"project_root": tmpdir})

        report_path = Path(tmpdir) / ".simflow" / "reports" / "orphan_compute_audit.md"
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "Orphan Compute" in content
        assert "stage1_vasp_relax" in content


def test_scanner_respects_max_depth():
    """Scanner respects max_depth parameter."""
    execute = _import_scanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        _init(tmpdir)
        # Create deeply nested compute dir
        deep_dir = Path(tmpdir) / "a" / "b" / "c" / "d" / "compute"
        deep_dir.mkdir(parents=True)
        (deep_dir / "OUTCAR").write_text("output\n", encoding="utf-8")

        # With max_depth=2, should NOT find the deep dir
        result = execute({"project_root": tmpdir, "max_depth": 2})
        orphan_paths = [d["path"] for d in result["data"]["orphan_dirs"]]
        assert not any("a/b/c/d" in p for p in orphan_paths)

        # With max_depth=5, should find it
        result = execute({"project_root": tmpdir, "max_depth": 5})
        orphan_paths = [d["path"] for d in result["data"]["orphan_dirs"]]
        assert any("a/b/c/d" in p for p in orphan_paths)


def test_scanner_requires_project_root():
    """Scanner requires project_root parameter."""
    execute = _import_scanner()

    result = execute({})
    assert result["status"] == "error"
    assert "project_root" in result["message"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
