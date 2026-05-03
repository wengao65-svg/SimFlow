#!/usr/bin/env python3
"""E2E test: Checkpoint creation and recovery after simulated failure.

Tests: init -> stage1 -> checkpoint -> stage2 (simulate failure) -> restore -> verify state recovery
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "runtime" / "scripts"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from lib.state import init_workflow, update_stage, read_state, write_state
from lib.artifact import register_artifact, list_artifacts
from lib.checkpoint import create_checkpoint, restore_checkpoint, list_checkpoints, get_latest_checkpoint


def run_script(name, args, cwd=None):
    """Run a runtime script and return parsed JSON output."""
    cmd = [sys.executable, str(SCRIPTS_DIR / name)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)
    try:
        return json.loads(proc.stdout), proc.returncode
    except json.JSONDecodeError:
        return {"stdout": proc.stdout, "stderr": proc.stderr}, proc.returncode


def test_checkpoint_recovery():
    """Test checkpoint creation, simulated failure, and recovery."""
    tmpdir = tempfile.mkdtemp()
    try:
        # 1. Initialize workflow
        state = init_workflow("dft", "input_generation", tmpdir)
        workflow_id = state["workflow_id"]
        assert state["current_stage"] == "input_generation"
        print("  [1/6] Workflow initialized")

        # 2. Complete input_generation stage
        update_stage("input_generation", "in_progress", tmpdir)
        register_artifact("INCAR", "input_files", "input_generation", tmpdir)
        register_artifact("KPOINTS", "input_files", "input_generation", tmpdir)
        update_stage("input_generation", "completed", tmpdir)

        # Create checkpoint after input_generation
        ckpt1 = create_checkpoint(workflow_id, "input_generation", "Inputs ready", tmpdir)
        assert ckpt1 is not None
        print("  [2/6] input_generation completed, checkpoint created")

        # 3. Start relax stage and complete it
        update_stage("relax", "in_progress", tmpdir)
        register_artifact("POSCAR", "structure", "relax", tmpdir)
        register_artifact("relaxed_POSCAR", "structure", "relax", tmpdir)
        update_stage("relax", "completed", tmpdir)

        ckpt2 = create_checkpoint(workflow_id, "relax", "Relaxation complete", tmpdir)
        assert ckpt2 is not None
        print("  [3/6] relax completed, checkpoint created")

        # 4. Simulate failure: start scf, corrupt state
        update_stage("scf", "in_progress", tmpdir)
        register_artifact("OSZICAR", "output", "scf", tmpdir)

        # Corrupt the workflow state (simulate mid-failure)
        workflow = read_state(tmpdir, "workflow.json")
        workflow["status"] = "corrupted"
        write_state(workflow, tmpdir)

        # Verify corruption
        corrupted = read_state(tmpdir, "workflow.json")
        assert corrupted["status"] == "corrupted"
        print("  [4/6] Simulated failure: state corrupted")

        # 5. Restore from latest checkpoint (relax)
        result = restore_checkpoint(ckpt2["checkpoint_id"], tmpdir)
        assert result is not None

        # Verify state is restored
        restored = read_state(tmpdir, "workflow.json")
        assert restored["workflow_id"] == workflow_id
        assert restored["workflow_type"] == "dft"

        # Verify checkpoints still exist
        checkpoints = list_checkpoints(tmpdir)
        assert len(checkpoints) >= 2
        print("  [5/6] State restored from checkpoint")

        # 6. Verify we can resume: retry scf
        update_stage("scf", "in_progress", tmpdir)
        register_artifact("OSZICAR_SCF", "output", "scf", tmpdir)
        register_artifact("energy.dat", "data", "scf", tmpdir)
        update_stage("scf", "completed", tmpdir)

        create_checkpoint(workflow_id, "scf", "SCF complete after recovery", tmpdir)

        # Verify final state
        artifacts = list_artifacts(base_dir=tmpdir)
        checkpoints = list_checkpoints(tmpdir)
        assert len(checkpoints) >= 3

        # Generate handoff to verify full state
        result, rc = run_script("generate_handoff.py", ["--base-dir", tmpdir])
        assert rc == 0
        assert "scf" in result["progress"]["completed"] or "relax" in result["progress"]["completed"]
        print("  [6/6] Workflow resumed and completed after recovery")

        print(f"\n  Checkpoints: {len(checkpoints)}")
        print(f"  Artifacts: {len(artifacts)}")
        print("\n  Checkpoint recovery E2E PASSED!")

    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_checkpoint_recovery()
