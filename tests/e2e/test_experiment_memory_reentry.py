"""End-to-end recovery of scientific intent from compact Experiment memory."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MCP_DIR = ROOT / "mcp" / "servers" / "simflow_state"
sys.path.insert(0, str(MCP_DIR))
sys.path.insert(0, str(ROOT))


def _load_state_server():
    for name in [key for key in sys.modules if key == "tools" or key.startswith("tools.")]:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location("memory_reentry_state_server", MCP_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record(server, params):
    result = server.handle_request({"tool": "record", "params": params})
    assert result["status"] == "success", result
    return result["data"]


def test_later_request_recovers_temperature_filter_decision_and_outcome(tmp_path):
    workdir = tmp_path / "stage6_NEP" / "NEPv3" / "dataset"
    workdir.mkdir(parents=True)
    source = workdir / "candidate_frames.jsonl"
    retained = workdir / "training_frames.jsonl"
    frames = [
        {"frame_id": index, "temperature_k": 400 + index}
        if index < 19 else {"frame_id": index, "temperature_k": 300 + index % 90}
        for index in range(215)
    ]
    source.write_text("".join(json.dumps(frame) + "\n" for frame in frames), encoding="utf-8")

    server = _load_state_server()
    experiment = _record(server, {
        "project_root": str(tmp_path),
        "channel": "experiment",
        "entry_type": "experiment",
        "summary": "Define the NEPv3 temperature-domain dataset question",
        "payload": {
            "title": "NEPv3 temperature-domain dataset",
            "research_question": "Should frames with temperature >= 400 K be excluded from NEPv3 training?",
            "scope_paths": [str(workdir.relative_to(tmp_path))],
            "tags": ["nep", "dataset", "temperature"],
        },
    })
    experiment_id = experiment["experiment_id"]
    attempt = _record(server, {
        "project_root": str(tmp_path),
        "channel": "experiment",
        "entry_type": "attempt",
        "summary": "Evaluate the 400 K exclusion criterion",
        "experiment_id": experiment_id,
        "payload": {
            "method": "deterministic frame filter",
            "parameters": {"exclude": "temperature_k >= 400"},
            "acceptance_criteria": {"source_frames": 215},
        },
    })
    attempt_id = attempt["entry"]["attempt_id"]

    retained_frames = [frame for frame in frames if frame["temperature_k"] < 400]
    retained.write_text(
        "".join(json.dumps(frame) + "\n" for frame in retained_frames),
        encoding="utf-8",
    )
    assert len(frames) == 215
    assert len(frames) - len(retained_frames) == 19
    assert len(retained_frames) == 196

    change = _record(server, {
        "project_root": str(tmp_path),
        "kind": "evidence_change",
        "summary": "Removed 19 high-temperature frames and retained 196 frames",
        "operation": "filter",
        "targets": [str(source.relative_to(tmp_path))],
        "before_refs": [str(source.relative_to(tmp_path))],
        "after_refs": [str(retained.relative_to(tmp_path))],
        "outcome": "completed",
        "experiment_id": experiment_id,
        "attempt_id": attempt_id,
    })
    _record(server, {
        "project_root": str(tmp_path),
        "channel": "experiment",
        "entry_type": "observation",
        "summary": "The 400 K criterion removed 19 frames and retained 196",
        "experiment_id": experiment_id,
        "runtime_record_ids": [change["record_id"]],
        "payload": {
            "attempt_id": attempt_id,
            "evidence": [str(retained.relative_to(tmp_path))],
            "details": {"before": 215, "removed": 19, "after": 196},
        },
    })
    decision = _record(server, {
        "project_root": str(tmp_path),
        "channel": "experiment",
        "entry_type": "decision",
        "summary": "Use the retained 196-frame dataset for NEPv3 training",
        "experiment_id": experiment_id,
        "runtime_record_ids": [change["record_id"]],
        "payload": {
            "attempt_id": attempt_id,
            "rationale": "The excluded frames were outside the accepted training temperature domain",
            "next_action": "Train NEPv3 with the retained dataset",
        },
    })

    later_server = _load_state_server()
    recovered = later_server.handle_request({
        "tool": "inspect",
        "params": {
            "project_root": str(tmp_path),
            "working_directory": str(workdir),
            "query": "What happened to the temperature >= 400 K frames for NEPv3?",
        },
    })

    assert recovered["status"] == "success"
    memory = recovered["data"]["experiment_memory"]
    assert memory["selected_experiment_id"] == experiment_id
    assert {entry["entry_type"] for entry in memory["entries"]} == {
        "experiment", "attempt", "observation", "decision",
    }
    assert memory["entries"][-1]["runtime_record_ids"] == [change["record_id"]]
    assert memory["operational_records"][-1]["kind"] == "evidence_change"
    assert memory["operational_records"][-1]["after_refs"][0]["path"] == str(retained.relative_to(tmp_path))
    assert recovered["data"]["project"]["current"]["next_action"] == "Train NEPv3 with the retained dataset"
    assert decision["entry"]["runtime_record_ids"] == [change["record_id"]]
