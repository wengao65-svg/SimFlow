#!/usr/bin/env python3
"""E2E test: Full MD workflow chain via runtime scripts.

Tests: init -> build -> forcefield -> equilibrate -> production -> parse_lammps -> checkpoint -> handoff
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "runtime" / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def run_script(name, args, cwd=None):
    """Run a runtime script and return parsed JSON output."""
    cmd = [sys.executable, str(SCRIPTS_DIR / name)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)
    try:
        return json.loads(proc.stdout), proc.returncode
    except json.JSONDecodeError:
        return {"stdout": proc.stdout, "stderr": proc.stderr}, proc.returncode


def test_md_workflow_e2e():
    """Full MD workflow E2E: init -> stages -> parse -> checkpoint -> handoff."""
    tmpdir = tempfile.mkdtemp()
    try:
        # 1. Initialize MD workflow
        result, rc = run_script("init_simflow_state.py", [
            "--workflow-type", "md", "--entry-point", "modeling", "--base-dir", tmpdir
        ])
        assert rc == 0
        assert result["workflow_type"] == "md"
        workflow_id = result["workflow_id"]
        print("  [1/8] MD workflow initialized")

        # 2. Modeling stage
        result, rc = run_script("transition_stage.py", [
            "--stage", "modeling", "--status", "in_progress", "--base-dir", tmpdir
        ])
        assert rc == 0

        from runtime.lib.artifact import register_artifact
        register_artifact("Si_4x4x4.cif", "structure", "modeling", tmpdir)

        result, rc = run_script("transition_stage.py", [
            "--stage", "modeling", "--status", "completed", "--base-dir", tmpdir
        ])
        assert rc == 0
        print("  [2/7] Modeling completed")

        # 3. Input generation
        result, rc = run_script("transition_stage.py", [
            "--stage", "input_generation", "--status", "in_progress", "--base-dir", tmpdir
        ])
        assert rc == 0

        register_artifact("Si.data", "input_files", "input_generation", tmpdir)
        register_artifact("in.lammps", "input_files", "input_generation", tmpdir)
        register_artifact("Si.sw", "input_files", "input_generation", tmpdir)

        result, rc = run_script("transition_stage.py", [
            "--stage", "input_generation", "--status", "completed", "--base-dir", tmpdir
        ])
        assert rc == 0
        print("  [3/7] Input generation completed")

        # 4. Compute - parse LAMMPS output
        result, rc = run_script("transition_stage.py", [
            "--stage", "compute", "--status", "in_progress", "--base-dir", tmpdir
        ])
        assert rc == 0

        lammps_log = str(FIXTURES_DIR / "lammps_log.lammps")
        result, rc = run_script("parse_output.py", ["lammps", lammps_log])
        assert rc == 0
        print("  [4/7] LAMMPS log parsed")

        result, rc = run_script("transition_stage.py", [
            "--stage", "compute", "--status", "completed", "--base-dir", tmpdir
        ])
        assert rc == 0

        result, rc = run_script("create_checkpoint.py", [
            "--workflow-id", workflow_id, "--stage", "compute",
            "--description", "MD production complete", "--base-dir", tmpdir
        ])
        assert rc == 0
        print("  [5/7] Compute completed, checkpoint created")

        # 5. Analysis
        result, rc = run_script("transition_stage.py", [
            "--stage", "analysis", "--status", "in_progress", "--base-dir", tmpdir
        ])
        assert rc == 0

        register_artifact("rdf_si.png", "plot", "analysis", tmpdir)
        register_artifact("msd.png", "plot", "analysis", tmpdir)
        register_artifact("thermodynamics.png", "plot", "analysis", tmpdir)
        register_artifact("analysis_summary.json", "data", "analysis", tmpdir)

        result, rc = run_script("transition_stage.py", [
            "--stage", "analysis", "--status", "completed", "--base-dir", tmpdir
        ])
        assert rc == 0
        print("  [6/7] Analysis completed")

        # 6. Handoff
        result, rc = run_script("generate_handoff.py", ["--base-dir", tmpdir])
        assert rc == 0
        assert result["workflow_type"] == "md"
        assert len(result["progress"]["completed"]) >= 4
        print("  [7/7] Handoff generated")

        print("\n  E2E MD workflow PASSED!")

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_md_workflow_e2e()
