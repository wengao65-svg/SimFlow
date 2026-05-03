#!/usr/bin/env python3
"""Tests for prepare_job.py skill script."""

import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "skills" / "simflow-compute" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
# Also add runtime/lib for hpc module
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_slurm_script_generation():
    from prepare_job import prepare_slurm_job
    config = {
        "job_name": "test_job",
        "executable": "mpirun vasp_std",
        "nodes": 2,
        "ntasks": 32,
        "time": "04:00:00",
        "partition": "normal",
    }
    result = prepare_slurm_job(config)
    assert result["scheduler"] == "slurm"
    assert "#SBATCH" in result["script"]
    assert "test_job" in result["script"]
    assert "vasp_std" in result["script"]


def test_pbs_script_generation():
    from prepare_job import prepare_pbs_job
    config = {
        "job_name": "test_job",
        "executable": "mpirun pw.x",
        "nodes": 1,
        "ppn": 16,
        "walltime": "02:00:00",
    }
    result = prepare_pbs_job(config)
    assert result["scheduler"] == "pbs"
    assert "#PBS" in result["script"]
    assert "pw.x" in result["script"]


def test_prepare_job_with_output():
    from prepare_job import prepare_job
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "job_name": "si_scf",
            "executable": "vasp_std",
            "software": "vasp",
            "num_atoms": 2,
        }
        result = prepare_job(config, "slurm", tmpdir, dry_run=True)
        assert result["status"] == "success"
        assert os.path.exists(result["script_path"])
        assert result["dry_run"] is True


def test_resource_estimation():
    from prepare_job import prepare_job
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "job_name": "big_calc",
            "executable": "vasp_std",
            "software": "vasp",
            "job_type": "relax",
            "num_atoms": 200,
        }
        result = prepare_job(config, "slurm", tmpdir, dry_run=True)
        assert result["resource_estimate"] is not None
        assert result["resource_estimate"]["recommended_nodes"] >= 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
