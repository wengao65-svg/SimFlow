#!/usr/bin/env python3
"""Integration tests for the compact HPC MCP surface."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from runtime.simflow_core.experiment_notebook import append_experiment_entry, create_experiment
from runtime.simflow_core.gates import record_gate_decision
from runtime.simflow_core.records import list_project_records, record_event
from runtime.simflow_helpers.computation.job_records import record_submit_job


SERVER_DIR = Path(__file__).resolve().parents[2] / "mcp" / "servers" / "hpc"


def _load_server():
    for name in [key for key in sys.modules if key == "connectors" or key.startswith("connectors.")]:
        del sys.modules[name]
    sys.path.insert(0, str(SERVER_DIR))
    spec = importlib.util.spec_from_file_location("hpc_server", SERVER_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_local_files(root: Path) -> tuple[Path, Path]:
    script = root / "job.sh"
    input_file = root / "input.dat"
    script.write_text("#!/bin/bash\necho local-ok\n", encoding="utf-8")
    script.chmod(0o755)
    input_file.write_text("input\n", encoding="utf-8")
    return script, input_file


def _plan_local(server, root: Path) -> dict:
    _make_local_files(root)
    result = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(root),
            "script_path": "job.sh",
            "input_paths": ["input.dat"],
            "scheduler": "local",
            "resources": {"nodes": 1, "ntasks": 1, "walltime": "00:05:00"},
        },
    })
    assert result["status"] == "success", result
    return result["data"]


def _approve(root: Path, run_plan_hash: str, gate: str = "hpc_submit") -> dict:
    return record_gate_decision(
        gate,
        "approved",
        {"run_plan_hash": run_plan_hash, "reason": "pytest immutable plan approval"},
        project_root=str(root),
        agent="pytest",
    )


def _create_attempt(root: Path, experiment_id: str, attempt_id: str) -> str:
    return append_experiment_entry(
        str(root),
        experiment_id=experiment_id,
        entry_type="attempt",
        attempt_id=attempt_id,
        summary=f"Scientific strategy {attempt_id}",
    )["entry"]["attempt_id"]


def test_tools_surface_is_exactly_four_composite_actions():
    from mcp.shared.stdio_server import _list_tools

    server = _load_server()
    listed = _list_tools(server.TOOLS, server.TOOL_DESCRIPTIONS, server.TOOL_SCHEMAS)
    schemas = {tool["name"]: tool["inputSchema"] for tool in listed}

    assert set(schemas) == {"plan", "transfer", "submit", "status"}
    assert set(schemas["plan"]["required"]) == {"project_root", "script_path", "input_paths"}
    assert set(schemas["transfer"]["required"]) == {"project_root", "run_plan_hash", "direction"}
    assert set(schemas["submit"]["required"]) == {"project_root", "run_plan_hash"}
    for removed in ("dry_run_evidence", "script_hash", "input_artifact_hash", "session_context_id"):
        assert removed not in schemas["submit"]["properties"]


def test_plan_validates_existing_script_and_persists_hash(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)

    assert len(plan["run_plan_hash"]) == 64
    assert plan["scheduler"] == "local"
    assert plan["script"]["path"] == "job.sh"
    assert plan["inputs"]["file_count"] == 2
    assert plan["resources"]["nodes"] == 1
    assert (tmp_path / plan["plan_path"]).is_file()


def test_plan_can_generate_and_validate_slurm_script(tmp_path):
    server = _load_server()
    (tmp_path / "INCAR").write_text("SYSTEM = test\n", encoding="utf-8")
    result = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(tmp_path),
            "script_path": "submit.sh",
            "input_paths": ["INCAR"],
            "scheduler": "slurm",
            "generate": {
                "job_name": "si_relax",
                "executable": "vasp_std",
                "nodes": 2,
                "ntasks": 32,
                "walltime": "04:00:00",
            },
        },
    })

    assert result["status"] == "success", result
    assert result["data"]["script_generated"] is True
    assert "#SBATCH" in (tmp_path / "submit.sh").read_text(encoding="utf-8")
    assert result["data"]["resources"] == {"nodes": 2, "ntasks": 32, "walltime": "04:00:00"}


def test_plan_fails_closed_on_credential_pattern(tmp_path):
    server = _load_server()
    script, input_file = _make_local_files(tmp_path)
    input_file.write_text("api_key=do-not-store\n", encoding="utf-8")
    result = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(tmp_path),
            "script_path": script.name,
            "input_paths": [input_file.name],
            "scheduler": "local",
        },
    })

    assert result["status"] == "error"
    assert result["data"]["credential_scan"]["status"] == "fail"
    assert "do-not-store" not in str(result)


def test_submit_requires_approval_bound_to_run_plan(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    result = server.handle_request({
        "tool": "submit",
        "params": {"project_root": str(tmp_path), "run_plan_hash": plan["run_plan_hash"]},
    })

    assert result["status"] == "error"
    assert result["approval_required"] is True
    assert result["run_plan_hash"] == plan["run_plan_hash"]


def test_submit_rejects_approval_for_different_plan(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    decision = _approve(tmp_path, "0" * 64)
    result = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "gate_decision_id": decision["decision_id"],
        },
    })

    assert result["status"] == "error"
    assert result["code"] == "run_plan_approval_mismatch"


def test_local_submit_executes_and_records_plan_plus_submit(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    result = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "gate_decision_id": decision["decision_id"],
        },
    })

    assert result["status"] == "success"
    assert "local-ok" in result["stdout"]
    assert result["run_plan_hash"] == plan["run_plan_hash"]
    records = list_project_records(str(tmp_path), kind="run")
    assert [record["details"]["operation"] for record in records] == ["plan", "submit"]
    assert records[-1]["details"]["run_plan_hash"] == plan["run_plan_hash"]
    assert not (tmp_path / ".simflow" / "state" / "jobs.json").exists()


def test_public_compact_approval_record_authorizes_submit(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    approval = record_event(
        str(tmp_path),
        kind="approval",
        summary="Approve immutable local run",
        status="approved",
        details={
            "gate": "hpc_submit",
            "conditions": {"run_plan_hash": plan["run_plan_hash"]},
            "agent": "pytest",
        },
    )
    result = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "gate_decision_id": approval["record_id"],
        },
    })

    assert result["status"] == "success"
    assert result["gate_decision_id"] == approval["record_id"]


def test_unchanged_retry_reuses_same_approval(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    request = {
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "gate_decision_id": decision["decision_id"],
        },
    }

    first = server.handle_request(request)
    second = server.handle_request(request)

    assert first["status"] == second["status"] == "success"
    assert len(list_project_records(str(tmp_path), kind="run")) == 3


def test_experiment_binding_does_not_change_run_plan_hash_or_prior_approval(tmp_path):
    server = _load_server()
    _make_local_files(tmp_path)
    first_experiment = create_experiment(
        str(tmp_path), title="Question A", research_question="Does A work?", scope_paths=["."],
    )["experiment_id"]
    second_experiment = create_experiment(
        str(tmp_path), title="Question B", research_question="Does B work?", scope_paths=["."],
    )["experiment_id"]
    params = {
        "project_root": str(tmp_path),
        "script_path": "job.sh",
        "input_paths": ["input.dat"],
        "scheduler": "local",
    }
    first = server.handle_request({"tool": "plan", "params": {**params, "experiment_id": first_experiment}})
    approval = _approve(tmp_path, first["data"]["run_plan_hash"])
    corrected = server.handle_request({"tool": "plan", "params": {**params, "experiment_id": second_experiment}})

    assert corrected["data"]["run_plan_hash"] == first["data"]["run_plan_hash"]
    assert corrected["binding"]["operation"] == "binding_correction"
    assert corrected["binding"]["experiment_id"] == second_experiment
    plan_payload = json.loads((tmp_path / corrected["data"]["plan_path"]).read_text(encoding="utf-8"))
    assert "experiment_id" not in plan_payload
    assert "attempt_id" not in plan_payload

    submitted = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": corrected["data"]["run_plan_hash"],
            "gate_decision_id": approval["decision_id"],
        },
    })
    assert submitted["status"] == "success"
    submit_record = list_project_records(str(tmp_path), kind="run")[-1]
    assert submit_record["experiment_id"] == second_experiment
    assert "attempt_id" not in submit_record
    assert corrected["binding"]["attempt_id"] is None


def test_hpc_only_consumes_explicit_attempt_references(tmp_path):
    server = _load_server()
    _make_local_files(tmp_path)
    experiment_id = create_experiment(
        str(tmp_path), title="Question", research_question="Which strategy works?", scope_paths=["."],
    )["experiment_id"]
    attempt_id = _create_attempt(tmp_path, experiment_id, "att_expanded_training")
    params = {
        "project_root": str(tmp_path), "script_path": "job.sh", "input_paths": ["input.dat"],
        "scheduler": "local",
    }

    experiment_only = server.handle_request({
        "tool": "plan", "params": {**params, "experiment_id": experiment_id},
    })
    bound = server.handle_request({
        "tool": "plan", "params": {**params, "experiment_id": experiment_id, "attempt_id": attempt_id},
    })
    attempt_only = server.handle_request({
        "tool": "plan", "params": {**params, "attempt_id": attempt_id},
    })
    unknown_attempt = server.handle_request({
        "tool": "plan", "params": {**params, "experiment_id": experiment_id, "attempt_id": "att_missing"},
    })

    assert experiment_only["binding"]["attempt_id"] is None
    assert bound["binding"]["attempt_id"] == attempt_id
    assert attempt_only["status"] == "error"
    assert "requires experiment_id" in attempt_only["message"]
    assert unknown_attempt["status"] == "error"
    assert "Unknown attempt_id" in unknown_attempt["message"]


def test_bound_status_records_only_real_transitions(tmp_path, monkeypatch):
    server = _load_server()
    _make_local_files(tmp_path)
    experiment_id = create_experiment(
        str(tmp_path), title="Status question", research_question="Did the run finish?", scope_paths=["."],
    )["experiment_id"]
    attempt_id = _create_attempt(tmp_path, experiment_id, "att_status_validation")
    planned = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(tmp_path), "script_path": "job.sh", "input_paths": ["input.dat"],
            "scheduler": "local", "experiment_id": experiment_id, "attempt_id": attempt_id,
        },
    })
    run_plan_hash = planned["data"]["run_plan_hash"]
    approval = _approve(tmp_path, run_plan_hash)
    record_submit_job(
        project_root=str(tmp_path), scheduler="slurm", job_id="12345", run_plan_hash=run_plan_hash,
        status="submitted", gate_decision_id=approval["decision_id"],
        experiment_id=experiment_id, attempt_id=attempt_id,
    )

    states = iter(["RUNNING", "RUNNING", "COMPLETED"])

    class StatusConnector:
        def status(self, job_id):
            return {"status": "success", "data": {"job_id": job_id, "state": next(states)}}

    monkeypatch.setattr(server, "_get_connector", lambda scheduler, target=None: StatusConnector())
    request = {
        "tool": "status",
        "params": {
            "project_root": str(tmp_path), "run_plan_hash": run_plan_hash,
            "job_id": "12345", "scheduler": "slurm",
        },
    }
    first = server.handle_request(request)
    repeated = server.handle_request(request)
    terminal = server.handle_request(request)

    assert first["recorded_transition"] is True
    assert repeated["recorded_transition"] is False
    assert terminal["recorded_transition"] is True
    status_records = [
        record for record in list_project_records(str(tmp_path), kind="run")
        if record.get("details", {}).get("operation") == "status"
    ]
    assert [record["status"] for record in status_records] == ["running", "completed"]
    assert all(record["experiment_id"] == experiment_id for record in status_records)
    assert all(record["attempt_id"] == attempt_id for record in status_records)
    submit_record = next(
        record for record in list_project_records(str(tmp_path), kind="run")
        if record.get("details", {}).get("operation") == "submit"
    )
    assert all(record["run_id"] == submit_record["run_id"] for record in status_records)
    assert submit_record["run_id"] != attempt_id


def test_one_attempt_can_reference_multiple_independent_runs(tmp_path):
    experiment_id = create_experiment(
        str(tmp_path), title="Validation strategy", research_question="Is the model stable?", scope_paths=["."],
    )["experiment_id"]
    attempt_id = _create_attempt(tmp_path, experiment_id, "att_multirun_validation")
    run_plan_hash = "a" * 64
    approval = _approve(tmp_path, run_plan_hash)

    first = record_submit_job(
        project_root=str(tmp_path), scheduler="slurm", job_id="1001", run_plan_hash=run_plan_hash,
        gate_decision_id=approval["decision_id"], experiment_id=experiment_id, attempt_id=attempt_id,
    )["record"]
    second = record_submit_job(
        project_root=str(tmp_path), scheduler="slurm", job_id="1002", run_plan_hash=run_plan_hash,
        gate_decision_id=approval["decision_id"], experiment_id=experiment_id, attempt_id=attempt_id,
    )["record"]

    assert first["attempt_id"] == second["attempt_id"] == attempt_id
    assert first["run_id"] != second["run_id"]
    assert attempt_id not in {first["run_id"], second["run_id"]}


def test_status_does_not_bind_an_untracked_job_to_a_requested_plan(tmp_path, monkeypatch):
    server = _load_server()
    plan = _plan_local(server, tmp_path)

    class StatusConnector:
        def status(self, job_id):
            return {"status": "success", "data": {"job_id": job_id, "state": "RUNNING"}}

    monkeypatch.setattr(server, "_get_connector", lambda scheduler, target=None: StatusConnector())
    result = server.handle_request({
        "tool": "status",
        "params": {
            "project_root": str(tmp_path), "run_plan_hash": plan["run_plan_hash"],
            "job_id": "untracked", "scheduler": "slurm",
        },
    })

    assert result["recorded_transition"] is False
    assert "no recorded submit" in result["recording_reason"]
    assert [record["details"]["operation"] for record in list_project_records(str(tmp_path), kind="run")] == ["plan"]


def test_changed_input_invalidates_prior_approval(tmp_path):
    server = _load_server()
    plan = _plan_local(server, tmp_path)
    decision = _approve(tmp_path, plan["run_plan_hash"])
    (tmp_path / "input.dat").write_text("changed\n", encoding="utf-8")
    result = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": plan["run_plan_hash"],
            "gate_decision_id": decision["decision_id"],
        },
    })

    assert result["status"] == "error"
    assert result["code"] == "run_plan_stale"
    assert result["approval_required"] is True


def test_resources_and_target_change_run_plan_hash(tmp_path):
    server = _load_server()
    _make_local_files(tmp_path)
    common = {
        "project_root": str(tmp_path),
        "script_path": "job.sh",
        "input_paths": ["input.dat"],
        "scheduler": "ssh",
        "remote_workdir": "/scratch/job",
        "transfer": {"direction": "upload", "remote_dir": "/scratch/job"},
    }
    first = server.handle_request({"tool": "plan", "params": {
        **common, "target": {"host": "hpc-a"}, "resources": {"nodes": 1},
    }})["data"]
    second = server.handle_request({"tool": "plan", "params": {
        **common, "target": {"host": "hpc-b"}, "resources": {"nodes": 1},
    }})["data"]
    third = server.handle_request({"tool": "plan", "params": {
        **common, "target": {"host": "hpc-a"}, "resources": {"nodes": 2},
    }})["data"]

    assert len({first["run_plan_hash"], second["run_plan_hash"], third["run_plan_hash"]}) == 3


def test_ssh_submit_requires_verified_transfer_manifest(tmp_path):
    server = _load_server()
    _make_local_files(tmp_path)
    planned = server.handle_request({
        "tool": "plan",
        "params": {
            "project_root": str(tmp_path),
            "script_path": "job.sh",
            "input_paths": ["input.dat"],
            "scheduler": "ssh",
            "target": {"host": "hpc"},
            "remote_workdir": "/scratch/job",
            "transfer": {"direction": "upload", "remote_dir": "/scratch/job"},
        },
    })["data"]
    decision = _approve(tmp_path, planned["run_plan_hash"])
    result = server.handle_request({
        "tool": "submit",
        "params": {
            "project_root": str(tmp_path),
            "run_plan_hash": planned["run_plan_hash"],
            "gate_decision_id": decision["decision_id"],
        },
    })

    assert result["status"] == "error"
    assert result["code"] == "transfer_manifest_required"


def test_status_requires_target_for_ssh():
    server = _load_server()
    result = server.handle_request({"tool": "status", "params": {"job_id": "123", "scheduler": "ssh"}})
    assert result["status"] == "error"
    assert result["code"] == "target_required"


def test_unknown_tool_is_rejected():
    server = _load_server()
    result = server.handle_request({"tool": "dry_run", "params": {}})
    assert result["status"] == "error"
    assert result["code"] == "UNKNOWN_TOOL"
    assert result["message"] == "Unknown tool: dry_run"
