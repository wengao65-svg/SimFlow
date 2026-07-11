#!/usr/bin/env python3
"""Tests for helper script recording contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from runtime.simflow_core.helper_evidence import build_helper_evidence
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.state import init_workflow, read_state


def test_add_helper_recording_args_adds_parent_artifact_option():
    parser = argparse.ArgumentParser()

    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args(["--parent-artifact", "art_input_1", "--parent-artifact", "art_input_2"])

    assert args.parent_artifact == ["art_input_1", "art_input_2"]


def test_maybe_record_helper_run_records_canonical_metadata_and_parent_lineage(tmp_path, monkeypatch):
    init_workflow("custom", "analysis_visualization", project_root=str(tmp_path))
    script_path = tmp_path / "analysis" / "summarize.py"
    output_path = tmp_path / "analysis" / "summary.json"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("print('ok')\n", encoding="utf-8")
    output_path.write_text('{"status":"ok"}\n', encoding="utf-8")

    parser = argparse.ArgumentParser()
    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args(
        [
            "--project-root",
            str(tmp_path),
            "--record-helper-run",
            "--parent-artifact",
            "art_parent_1",
            "--parent-artifact",
            "art_parent_2",
        ]
    )
    monkeypatch.setattr(sys, "argv", ["summarize.py", "--record-helper-run"])

    result = {
        "status": "needs_inputs",
        "output": "analysis/summary.json",
        "helper_evidence": build_helper_evidence(
            helper="summarize_metrics",
            capability="analysis_summary",
            status="warning",
            stage="analysis_visualization",
            activity="analysis_summary",
            evidence_role="summary_report",
            parser_status="partial",
        ),
    }

    recorded = maybe_record_helper_run(
        args=args,
        result=result,
        script_path=script_path,
        helper_name="summarize_metrics",
        metadata={
            "output_metadata": {
                "format": "json",
                "simflow_result": {"outcome": "error", "corrupted": True},
                "helper_evidence": {"status": "error", "corrupted": True},
                "helper_evidence_summary": {"helper_status": "error", "corrupted": True},
            }
        },
    )

    artifacts = read_state(project_root=str(tmp_path), state_file="artifacts.json")
    output_artifact = next(artifact for artifact in artifacts if artifact["type"] == "helper_output")
    manifest_artifact = next(artifact for artifact in artifacts if artifact["type"] == "helper_run_manifest")
    manifest_path = tmp_path / manifest_artifact["path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert recorded["status"] == "needs_inputs"
    assert output_artifact["metadata"]["format"] == "json"
    assert output_artifact["metadata"]["simflow_result"]["legacy_status"] == "needs_inputs"
    assert output_artifact["metadata"]["simflow_result"]["outcome"] == "waiting"
    assert "corrupted" not in output_artifact["metadata"]["simflow_result"]
    assert output_artifact["metadata"]["helper_evidence"]["schema_version"] == "simflow.helper_evidence.v1"
    assert output_artifact["metadata"]["helper_evidence"]["status"] == "warning"
    assert "corrupted" not in output_artifact["metadata"]["helper_evidence"]
    assert output_artifact["metadata"]["helper_evidence_summary"]["helper_status"] == "warning"
    assert "corrupted" not in output_artifact["metadata"]["helper_evidence_summary"]
    assert output_artifact["lineage"]["parent_artifacts"][:2] == ["art_parent_1", "art_parent_2"]
    assert manifest_artifact["lineage"]["parent_artifacts"][:2] == ["art_parent_1", "art_parent_2"]
    assert manifest_artifact["metadata"]["simflow_result"]["legacy_status"] == "needs_inputs"
    assert manifest_artifact["metadata"]["helper_evidence"]["schema_version"] == "simflow.helper_evidence.v1"
    assert manifest["metadata"]["simflow_result"]["legacy_status"] == "needs_inputs"


def test_maybe_record_helper_run_mutates_existing_helper_state_effect_to_record_only(tmp_path, monkeypatch):
    init_workflow("custom", "analysis_visualization", project_root=str(tmp_path))
    script_path = tmp_path / "analysis.py"
    output_path = tmp_path / "report.json"
    script_path.write_text("print('ok')\n", encoding="utf-8")
    output_path.write_text('{"status":"ok"}\n', encoding="utf-8")

    parser = argparse.ArgumentParser()
    add_helper_recording_args(parser, default_stage="analysis_visualization")
    args = parser.parse_args(["--project-root", str(tmp_path), "--record-helper-run"])
    monkeypatch.setattr(sys, "argv", ["analysis.py", "--record-helper-run"])

    result = {
        "status": "success",
        "output": str(output_path),
        "simflow_result": {
            "schema_version": "simflow.result.v1",
            "role": "helper",
            "activity": "analysis",
            "legacy_status": "success",
            "outcome": "success",
            "stage": "analysis_visualization",
            "state_effect": "none",
        },
    }

    recorded = maybe_record_helper_run(
        args=args,
        result=result,
        script_path=script_path,
        helper_name="analysis_helper",
    )

    artifacts = read_state(project_root=str(tmp_path), state_file="artifacts.json")
    manifest_artifact = next(artifact for artifact in artifacts if artifact["type"] == "helper_run_manifest")
    manifest = json.loads((tmp_path / manifest_artifact["path"]).read_text(encoding="utf-8"))
    checkpoints = read_state(project_root=str(tmp_path), state_file="checkpoints.json")
    stages = read_state(project_root=str(tmp_path), state_file="stages.json")

    assert recorded["simflow_result"]["state_effect"] == "record_only"
    assert recorded["simflow_result"]["outcome"] == "success"
    assert manifest["metadata"]["simflow_result"]["state_effect"] == "record_only"
    assert manifest_artifact["metadata"]["simflow_result"]["state_effect"] == "record_only"
    assert checkpoints == []
    assert stages == {}
