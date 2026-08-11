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
        "action": "create",
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
        "action": "define",
        "summary": "Evaluate the 400 K exclusion criterion",
        "experiment_id": experiment_id,
        "payload": {
            "method": "deterministic frame filter",
            "parameters": {"exclude": "temperature_k >= 400"},
            "acceptance_criteria": {"source_frames": 215},
        },
    })
    attempt_id = attempt["entry"]["attempt_id"]
    planned = _record(server, {
        "project_root": str(tmp_path),
        "channel": "experiment",
        "entry_type": "material_action",
        "action": "filter_dataset",
        "summary": "Plan exclusion of frames at or above 400 K",
        "experiment_id": experiment_id,
        "payload": {
            "attempt_id": attempt_id,
            "status": "planned",
            "operation": "filter",
            "targets": [str(source.relative_to(tmp_path))],
            "reason": "Keep training evidence within the accepted temperature domain",
            "selection_criteria": "temperature_k >= 400",
            "recoverability": "reversible",
            "evidence": [str(source.relative_to(tmp_path))],
        },
    })

    retained_frames = [frame for frame in frames if frame["temperature_k"] < 400]
    retained.write_text(
        "".join(json.dumps(frame) + "\n" for frame in retained_frames),
        encoding="utf-8",
    )
    assert len(frames) == 215
    assert len(frames) - len(retained_frames) == 19
    assert len(retained_frames) == 196

    material_action_id = planned["entry"]["details"]["material_action_id"]
    _record(server, {
        "project_root": str(tmp_path),
        "channel": "experiment",
        "entry_type": "material_action",
        "action": "filter_dataset",
        "summary": "Removed 19 high-temperature frames and retained 196 frames",
        "experiment_id": experiment_id,
        "payload": {
            "attempt_id": attempt_id,
            "status": "completed",
            "operation": "filter",
            "material_action_id": material_action_id,
            "outcome": {"before": 215, "removed": 19, "after": 196},
            "actual_scope": [str(retained.relative_to(tmp_path))],
            "evidence": [str(retained.relative_to(tmp_path))],
            "next_action": "Use the retained 196-frame dataset for NEPv3 training",
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
    completed = [
        entry for entry in memory["entries"]
        if entry["entry_type"] == "material_action" and entry.get("status") == "completed"
    ]
    assert len(completed) == 1
    assert completed[0]["details"]["material_action_id"] == material_action_id
    assert completed[0]["details"]["outcome"] == {"before": 215, "removed": 19, "after": 196}
    assert completed[0]["evidence"][0]["path"] == str(retained.relative_to(tmp_path))
    assert recovered["data"]["project"]["current"]["open_material_actions"] == []
    assert recovered["data"]["project"]["current"]["next_action"].startswith("Use the retained 196")
