"""Safety regression tests for explicit legacy-state migration."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from runtime.simflow_core.migration import MigrationError, apply_migration, build_migration_report
from runtime.simflow_core.records import inspect_project, list_project_records


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_migration_audit_is_read_only_and_indexes_only_structured_state_and_memory_metadata(tmp_path):
    legacy = tmp_path / ".simflow" / "state" / "workflow.json"
    memory_json = tmp_path / ".simflow" / "memory" / "experiments.json"
    memory_jsonl = tmp_path / ".simflow" / "memory" / "events.jsonl"
    memory_db = tmp_path / ".simflow" / "memory" / "ledger.sqlite3"
    memory_blob = tmp_path / ".simflow" / "memory" / "snapshot.bin"
    nested = tmp_path / "runs" / "case_a" / ".simflow" / "state" / "jobs.json"
    nested_memory = tmp_path / "runs" / "case_a" / ".simflow" / "memory" / "index.json"
    transcript = tmp_path / ".omx" / "session.json"
    result_data = tmp_path / "runs" / "case_a" / "trajectory.json"
    _write_json(
        legacy,
        {"workflow_id": "DO_NOT_EXPOSE", "status": "completed", "scientific_claim": "DO_NOT_IMPORT"},
    )
    _write_json(memory_json, {"experiment": "DO_NOT_IMPORT_MEMORY", "attempts": [1, 2]})
    memory_jsonl.parent.mkdir(parents=True, exist_ok=True)
    memory_jsonl.write_text('{"event":"DO_NOT_IMPORT_EVENT"}\n[1, 2]\n', encoding="utf-8")
    with sqlite3.connect(memory_db) as connection:
        connection.execute("CREATE TABLE private_memory (secret TEXT)")
        connection.execute("INSERT INTO private_memory VALUES ('DO_NOT_IMPORT_SQLITE')")
    memory_blob.write_bytes(b"DO_NOT_IMPORT_BINARY")
    _write_json(nested, [{"job_id": "DO_NOT_EXPOSE"}])
    _write_json(nested_memory, {"summary": "DO_NOT_IMPORT_NESTED_MEMORY"})
    _write_json(transcript, {"messages": ["DO_NOT_IMPORT_TRANSCRIPT"]})
    _write_json(result_data, {"energies": [1, 2, 3], "marker": "DO_NOT_IMPORT_RESULT"})
    source_bytes = {
        path: path.read_bytes()
        for path in (
            legacy, memory_json, memory_jsonl, memory_db, memory_blob,
            nested, nested_memory, transcript, result_data,
        )
    }

    report = build_migration_report(str(tmp_path))
    serialized = json.dumps(report, sort_keys=True)

    assert report["detected"] is True
    assert report["proposed_index"]["legacy_state"]["state_file_count"] == 1
    memory = report["proposed_index"]["legacy_memory"]
    assert memory["memory_file_count"] == 4
    assert memory["content_imported"] is False
    by_name = {Path(item["path"]).name: item for item in memory["memory_files"]}
    assert by_name["experiments.json"]["json_shape"] == {
        "valid_json": True, "json_type": "object", "entry_count": 2,
    }
    assert by_name["events.jsonl"]["jsonl_shape"] == {
        "valid_jsonl": True, "json_types": ["array", "object"], "entry_count": 2,
    }
    assert by_name["ledger.sqlite3"]["sqlite"]["format"] == "sqlite3"
    assert by_name["ledger.sqlite3"]["sqlite"]["tables_inspected"] is False
    assert "json_shape" not in by_name["snapshot.bin"]
    assert report["proposed_index"]["nested_simflow_roots"][0]["path"] == "runs/case_a/.simflow"
    assert report["proposed_index"]["nested_simflow_roots"][0]["state_file_count"] == 1
    assert report["proposed_index"]["nested_simflow_roots"][0]["memory_file_count"] == 1
    assert report["proposed_index"]["host_transcripts_imported"] is False
    assert "DO_NOT_EXPOSE" not in serialized
    assert "DO_NOT_IMPORT" not in serialized
    assert "private_memory" not in serialized
    assert all(path.read_bytes() == content for path, content in source_bytes.items())
    assert not (tmp_path / ".simflow" / "project.json").exists()
    assert not (tmp_path / ".simflow" / "records.jsonl").exists()
    assert not (tmp_path / ".simflow" / "reports").exists()


def test_migration_requires_confirmation_and_rejects_stale_inventory(tmp_path):
    legacy = tmp_path / ".simflow" / "state" / "workflow.json"
    _write_json(legacy, {"workflow_id": "wf_old"})
    report_hash = build_migration_report(str(tmp_path))["migration_report_hash"]

    with pytest.raises(MigrationError, match="confirm_migration=true"):
        apply_migration(
            str(tmp_path),
            migration_report_hash=report_hash,
            confirm_migration=False,
        )

    _write_json(legacy, {"workflow_id": "wf_changed"})
    with pytest.raises(MigrationError, match="stale"):
        apply_migration(
            str(tmp_path),
            migration_report_hash=report_hash,
            confirm_migration=True,
        )

    assert not (tmp_path / ".simflow" / "records.jsonl").exists()
    assert not (tmp_path / ".simflow" / "reports").exists()


def test_migration_hash_covers_legacy_memory_metadata(tmp_path):
    memory = tmp_path / ".simflow" / "memory" / "events.jsonl"
    memory.parent.mkdir(parents=True)
    memory.write_text('{"event":"first"}\n', encoding="utf-8")
    report_hash = build_migration_report(str(tmp_path))["migration_report_hash"]

    memory.write_text('{"event":"second"}\n', encoding="utf-8")

    with pytest.raises(MigrationError, match="stale"):
        apply_migration(
            str(tmp_path),
            migration_report_hash=report_hash,
            confirm_migration=True,
        )


def test_migration_confirmation_is_idempotent_and_preserves_sources(tmp_path):
    legacy = tmp_path / ".simflow" / "state" / "artifacts.json"
    nested = tmp_path / "legacy_run" / ".simflow" / "state" / "checkpoints.json"
    _write_json(legacy, [{"artifact_id": "art_old", "path": "result.dat"}])
    _write_json(nested, [{"checkpoint_id": "ckpt_old"}])
    source_bytes = {path: path.read_bytes() for path in (legacy, nested)}
    report_hash = build_migration_report(str(tmp_path))["migration_report_hash"]

    first = apply_migration(
        str(tmp_path),
        migration_report_hash=report_hash,
        confirm_migration=True,
    )
    second = apply_migration(
        str(tmp_path),
        migration_report_hash=report_hash,
        confirm_migration=True,
    )

    records = list_project_records(str(tmp_path), kind="migration")
    inspected = inspect_project(str(tmp_path), kind="migration")
    report_files = list((tmp_path / ".simflow" / "reports" / "migration").glob("*.json"))
    assert first["status"] == "applied"
    assert second["status"] == "already_applied"
    assert second["record"]["record_id"] == first["record"]["record_id"]
    assert len(records) == 1
    assert inspected["matched_count"] == 1
    assert inspected["records"][0]["record_id"] == first["record"]["record_id"]
    assert len(report_files) == 1
    assert report_files[0].stem == report_hash
    assert all(path.read_bytes() == content for path, content in source_bytes.items())
