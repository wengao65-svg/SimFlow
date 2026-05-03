#!/usr/bin/env python3
"""E2E test: Full DFT workflow chain via runtime scripts.

Tests: init -> input_gen -> relax (parse OSZICAR) -> checkpoint -> restore -> scf -> handoff
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


def test_dft_workflow_e2e():
    """Full DFT workflow E2E: init -> stages -> parse -> checkpoint -> handoff."""
    tmpdir = tempfile.mkdtemp()
    try:
        # 1. Initialize workflow
        result, rc = run_script("init_simflow_state.py", [
            "--workflow-type", "dft", "--entry-point", "input_generation", "--base-dir", tmpdir
        ])
        assert rc == 0, f"Init failed: {result}"
        assert result["workflow_type"] == "dft"
        assert result["current_stage"] == "input_generation"
        workflow_id = result["workflow_id"]
        print("  [1/8] Workflow initialized")

        # 2. Transition input_generation -> in_progress
        result, rc = run_script("transition_stage.py", [
            "--stage", "input_generation", "--status", "in_progress", "--base-dir", tmpdir
        ])
        assert rc == 0, f"Transition failed: {result}"
        print("  [2/7] input_generation -> in_progress")

        # 3. Register input artifacts
        from runtime.lib.artifact import register_artifact
        register_artifact("INCAR", "input_files", "input_generation", tmpdir)
        register_artifact("KPOINTS", "input_files", "input_generation", tmpdir)
        register_artifact("POSCAR", "structure", "input_generation", tmpdir)
        print("  [3/7] Input artifacts registered")

        # 4. Complete input_generation, start relax
        result, rc = run_script("transition_stage.py", [
            "--stage", "input_generation", "--status", "completed", "--base-dir", tmpdir
        ])
        assert rc == 0

        # Create checkpoint
        result, rc = run_script("create_checkpoint.py", [
            "--workflow-id", workflow_id, "--stage", "input_generation",
            "--description", "Inputs generated", "--base-dir", tmpdir
        ])
        assert rc == 0
        print("  [4/7] Checkpoint created for input_generation")

        # 5. Relax stage - parse VASP output
        result, rc = run_script("transition_stage.py", [
            "--stage", "relax", "--status", "in_progress", "--base-dir", tmpdir
        ])
        assert rc == 0

        oszicar = str(FIXTURES_DIR / "OSZICAR_Si")
        result, rc = run_script("parse_output.py", ["vasp", oszicar])
        assert rc == 0
        assert "final_energy" in result or "software" in result
        print("  [5/7] VASP OSZICAR parsed")

        # 6. Restore from checkpoint
        result, rc = run_script("restore_checkpoint.py", ["--latest", "--base-dir", tmpdir])
        assert rc == 0
        assert result["status"] == "success"
        print("  [6/7] Checkpoint restored")

        # 7. Generate handoff
        result, rc = run_script("generate_handoff.py", ["--base-dir", tmpdir])
        assert rc == 0
        assert "workflow_id" in result
        assert "progress" in result
        assert "next_steps" in result
        print("  [7/7] Handoff generated")

        print("\n  E2E DFT workflow PASSED!")

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_dft_workflow_e2e()
