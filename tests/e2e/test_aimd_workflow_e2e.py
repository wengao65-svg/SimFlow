#!/usr/bin/env python3
"""E2E test: Full AIMD workflow chain via runtime scripts.

Tests: init -> build -> generate_inputs -> parse_output -> checkpoint -> analyze -> handoff
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


def test_aimd_workflow_e2e():
    """Full AIMD workflow E2E: init -> stages -> parse -> checkpoint -> handoff."""
    tmpdir = tempfile.mkdtemp()
    try:
        # 1. Initialize AIMD workflow
        result, rc = run_script("init_simflow_state.py", [
            "--workflow-type", "aimd", "--entry-point", "modeling", "--base-dir", tmpdir
        ])
        assert rc == 0
        assert result["workflow_type"] == "aimd"
        workflow_id = result["workflow_id"]
        print("  [1/7] AIMD workflow initialized")

        # 2. Modeling stage
        result, rc = run_script("transition_stage.py", [
            "--stage", "modeling", "--status", "in_progress", "--base-dir", tmpdir
        ])
        assert rc == 0

        from runtime.lib.artifact import register_artifact
        register_artifact("Si.cif", "structure", "modeling", tmpdir)
        register_artifact("model.json", "model", "modeling", tmpdir)

        result, rc = run_script("transition_stage.py", [
            "--stage", "modeling", "--status", "completed", "--base-dir", tmpdir
        ])
        assert rc == 0

        result, rc = run_script("create_checkpoint.py", [
            "--workflow-id", workflow_id, "--stage", "modeling",
            "--description", "Structure built", "--base-dir", tmpdir
        ])
        assert rc == 0
        print("  [2/7] Modeling completed, checkpoint created")

        # 3. Input generation stage
        result, rc = run_script("transition_stage.py", [
            "--stage", "input_generation", "--status", "in_progress", "--base-dir", tmpdir
        ])
        assert rc == 0

        register_artifact("INCAR.md", "input_files", "input_generation", tmpdir)
        register_artifact("input_manifest.json", "input_manifest", "input_generation", tmpdir)

        result, rc = run_script("transition_stage.py", [
            "--stage", "input_generation", "--status", "completed", "--base-dir", tmpdir
        ])
        assert rc == 0
        print("  [3/7] Input generation completed")

        # 4. Compute stage - parse QE output
        result, rc = run_script("transition_stage.py", [
            "--stage", "compute", "--status", "in_progress", "--base-dir", tmpdir
        ])
        assert rc == 0

        qe_output = str(FIXTURES_DIR / "qe_output_Si.xml")
        result, rc = run_script("parse_output.py", ["qe", qe_output])
        assert rc == 0
        print("  [4/7] QE output parsed")

        result, rc = run_script("transition_stage.py", [
            "--stage", "compute", "--status", "completed", "--base-dir", tmpdir
        ])
        assert rc == 0

        result, rc = run_script("create_checkpoint.py", [
            "--workflow-id", workflow_id, "--stage", "compute",
            "--description", "AIMD run complete", "--base-dir", tmpdir
        ])
        assert rc == 0
        print("  [5/7] Compute completed, checkpoint created")

        # 5. Analysis stage
        result, rc = run_script("transition_stage.py", [
            "--stage", "analysis", "--status", "in_progress", "--base-dir", tmpdir
        ])
        assert rc == 0

        register_artifact("rdf.png", "plot", "analysis", tmpdir)
        register_artifact("msd.png", "plot", "analysis", tmpdir)
        register_artifact("trajectory_analysis.json", "data", "analysis", tmpdir)

        result, rc = run_script("transition_stage.py", [
            "--stage", "analysis", "--status", "completed", "--base-dir", tmpdir
        ])
        assert rc == 0
        print("  [6/7] Analysis completed")

        # 6. Generate handoff
        result, rc = run_script("generate_handoff.py", ["--base-dir", tmpdir])
        assert rc == 0
        assert result["workflow_type"] == "aimd"
        assert "modeling" in result["progress"]["completed"]
        assert "compute" in result["progress"]["completed"]
        assert "analysis" in result["progress"]["completed"]
        print("  [7/7] Handoff generated")

        print("\n  E2E AIMD workflow PASSED!")

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_aimd_workflow_e2e()
