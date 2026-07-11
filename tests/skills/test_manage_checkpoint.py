#!/usr/bin/env python3
"""Tests for the checkpoint state-admin skill wrapper."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from runtime.simflow_core.checkpoints import create_checkpoint
from runtime.simflow_core.state import init_workflow, read_state, update_stage


SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "simflow-checkpoint" / "scripts" / "manage_checkpoint.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("manage_checkpoint", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assert_state_admin_result(result: dict, *, activity: str, state_effect: str, outcome: str = "success") -> None:
    simflow_result = result["simflow_result"]
    assert simflow_result["schema_version"] == "simflow.result.v1"
    assert simflow_result["role"] == "state_admin"
    assert simflow_result["activity"] == activity
    assert simflow_result["outcome"] == outcome
    assert simflow_result["state_effect"] == state_effect


def test_manage_checkpoint_create_list_restore_latest_with_project_root(tmp_path):
    module = _load_module()
    workflow = init_workflow("dft", "modeling", project_root=str(tmp_path))
    update_stage("modeling", "completed", project_root=str(tmp_path), outputs=["art_model"])

    created = module.manage_checkpoint(str(tmp_path), "create")
    checkpoint_id = created["checkpoint"]["checkpoint_id"]

    assert created["status"] == "success"
    assert created["action"] == "create"
    assert created["project_root"] == str(tmp_path)
    assert created["checkpoint"]["workflow_id"] == workflow["workflow_id"]
    assert created["checkpoint"]["stage_id"] == "modeling"
    assert "helper_run_id" not in created
    _assert_state_admin_result(created, activity="checkpoint_create", state_effect="checkpoint_admin")

    listed = module.manage_checkpoint(str(tmp_path), "list")
    assert listed["status"] == "success"
    assert listed["action"] == "list"
    assert [item["checkpoint_id"] for item in listed["checkpoints"]] == [checkpoint_id]
    _assert_state_admin_result(listed, activity="checkpoint_list", state_effect="none")

    update_stage("computation", "completed", project_root=str(tmp_path), outputs=["art_compute"])
    restored = module.manage_checkpoint(str(tmp_path), "restore", checkpoint_id)
    stages_after_restore = read_state(project_root=str(tmp_path), state_file="stages.json")

    assert restored["status"] == "success"
    assert restored["action"] == "restore"
    assert restored["checkpoint_id"] == checkpoint_id
    assert "computation" not in stages_after_restore
    _assert_state_admin_result(restored, activity="checkpoint_restore", state_effect="checkpoint_admin")

    update_stage("computation", "completed", project_root=str(tmp_path), outputs=["art_compute"])
    second = create_checkpoint(workflow["workflow_id"], "computation", "After computation", project_root=str(tmp_path))
    update_stage("writing", "completed", project_root=str(tmp_path), outputs=["art_write"])

    latest = module.manage_checkpoint(str(tmp_path), "latest")
    stages_after_latest = read_state(project_root=str(tmp_path), state_file="stages.json")

    assert latest["status"] == "success"
    assert latest["action"] == "latest"
    assert latest["checkpoint"]["checkpoint_id"] == second["checkpoint_id"]
    assert "computation" in stages_after_latest
    assert "writing" not in stages_after_latest
    _assert_state_admin_result(latest, activity="checkpoint_latest", state_effect="checkpoint_admin")


def test_manage_checkpoint_accepts_simflow_dir_and_resolves_project_root(tmp_path):
    module = _load_module()
    workflow = init_workflow("dft", "modeling", project_root=str(tmp_path))
    checkpoint = create_checkpoint(workflow["workflow_id"], "modeling", "After modeling", project_root=str(tmp_path))

    listed = module.manage_checkpoint(str(tmp_path / ".simflow"), "list")

    assert listed["status"] == "success"
    assert listed["project_root"] == str(tmp_path)
    assert [item["checkpoint_id"] for item in listed["checkpoints"]] == [checkpoint["checkpoint_id"]]
    _assert_state_admin_result(listed, activity="checkpoint_list", state_effect="none")


def test_manage_checkpoint_cli_errors_keep_state_admin_result_contract(tmp_path):
    init_workflow("dft", "modeling", project_root=str(tmp_path))

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-root",
            str(tmp_path),
            "--action",
            "restore",
            "--checkpoint-id",
            "ckpt_missing",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] == "error"
    assert payload["action"] == "restore"
    assert payload["project_root"] == str(tmp_path)
    _assert_state_admin_result(
        payload,
        activity="checkpoint_restore",
        state_effect="checkpoint_admin",
        outcome="error",
    )
