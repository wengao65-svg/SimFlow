"""Transactional, forward-only experiment memory for cross-session continuity."""

from __future__ import annotations

import contextlib
import contextvars
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .state import resolve_project_path, resolve_project_root


MEMORY_DIR = Path(".simflow/memory")
DATABASE_FILE = "ledger.sqlite3"
LEDGER_FILE = "ledger.json"
EXPERIMENTS_FILE = "experiments.json"
ITERATIONS_FILE = "iterations.json"
ACTIVITY_EVENTS_FILE = "activity_events.jsonl"
SESSION_CONTEXTS_FILE = "session_contexts.jsonl"
SESSION_HANDOFFS_FILE = "session_handoffs.jsonl"
SUMMARY_FILE = "summary.json"
EVENTS_FILE = "events.jsonl"
LEDGER_SCHEMA_VERSION = "simflow.experiment_ledger.v2"
LEGACY_LEDGER_SCHEMA_VERSION = "simflow.experiment_ledger.v1"
SESSION_TIMEOUT_SECONDS = int(os.environ.get("SIMFLOW_SESSION_TIMEOUT_MIN", "30")) * 60
SQLITE_BUSY_TIMEOUT_MS = int(os.environ.get("SIMFLOW_LEDGER_BUSY_TIMEOUT_MS", "15000"))

EXPERIMENT_STATUSES = {"active", "paused", "completed", "failed", "abandoned", "superseded"}
EXPERIMENT_TERMINAL_STATUSES = {"completed", "failed", "abandoned", "superseded"}
ITERATION_STATUSES = {"running", "evaluating", "accepted", "rejected", "failed", "paused", "superseded"}
ITERATION_OPEN_STATUSES = {"running", "evaluating", "paused"}
ITERATION_TERMINAL_STATUSES = {"accepted", "rejected", "failed", "superseded"}
ACTIVITY_TERMINAL_STATUSES = {"completed", "partial", "failed", "paused", "cancelled"}
REFERENCE_KINDS = {"artifact", "checkpoint", "job", "gate", "path", "external"}

CONTEXT_ENV = {
    "session_context_id": "SIMFLOW_SESSION_CONTEXT_ID",
    "experiment_id": "SIMFLOW_EXPERIMENT_ID",
    "iteration_id": "SIMFLOW_ITERATION_ID",
    "activity_id": "SIMFLOW_ACTIVITY_ID",
}

_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|passwd|secret|authorization|private[_-]?key)"
)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|passwd|secret|authorization|private[_-]?key)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


class ExperimentMemoryError(ValueError):
    """Raised when experiment-memory state or context is invalid."""


class LedgerCorruptionError(ExperimentMemoryError):
    """Raised when an existing experiment ledger cannot be trusted."""


class LedgerUpgradeRequired(ExperimentMemoryError):
    """Raised when an unreleased v1 JSON ledger requires explicit migration."""


@dataclass(frozen=True)
class ExperimentContext:
    project_root: str
    session_context_id: str
    experiment_id: str
    activity_id: str
    iteration_id: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "project_root": self.project_root,
            "session_context_id": self.session_context_id,
            "experiment_id": self.experiment_id,
            "iteration_id": self.iteration_id,
            "activity_id": self.activity_id,
        }

    def environment(self) -> dict[str, str]:
        values = self.as_dict()
        return {
            env_name: str(values[field])
            for field, env_name in CONTEXT_ENV.items()
            if values.get(field)
        }


_ACTIVE_CONTEXT: contextvars.ContextVar[ExperimentContext | None] = contextvars.ContextVar(
    "simflow_experiment_context", default=None
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_epoch() -> float:
    return time.time()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _paths(root: Path) -> dict[str, Path]:
    base = root / MEMORY_DIR
    return {
        "base": base,
        "database": base / DATABASE_FILE,
        "ledger": base / LEDGER_FILE,
        "experiments": base / EXPERIMENTS_FILE,
        "iterations": base / ITERATIONS_FILE,
        "activities": base / ACTIVITY_EVENTS_FILE,
        "contexts": base / SESSION_CONTEXTS_FILE,
        "handoffs": base / SESSION_HANDOFFS_FILE,
        "summary": base / SUMMARY_FILE,
        "events": base / EVENTS_FILE,
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_load(value: str | None, default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise LedgerCorruptionError(f"Invalid JSON stored in experiment ledger: {error}") from error


def _read_json_file(path: Path, default: Any, *, strict: bool = False) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        if strict:
            raise LedgerCorruptionError(f"Cannot read {path}: {error}") from error
        return default


def _read_jsonl_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as error:
                    raise LedgerCorruptionError(f"Invalid JSONL in {path}:{line_number}: {error}") from error
                if not isinstance(value, dict):
                    raise LedgerCorruptionError(f"Expected object in {path}:{line_number}")
                records.append(value)
    except OSError as error:
        raise LedgerCorruptionError(f"Cannot read {path}: {error}") from error
    return records


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temp), str(path))
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def _write_jsonl_atomic(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(_canonical_json(record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temp), str(path))
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def _sanitize_text(value: str) -> str:
    result = _BEARER_PATTERN.sub("Bearer [REDACTED]", value)
    result = _SECRET_ASSIGNMENT_PATTERN.sub(r"\1\2[REDACTED]", result)
    if _PRIVATE_KEY_PATTERN.search(result):
        return "[REDACTED PRIVATE KEY MATERIAL]"
    return result


def sanitize_for_ledger(value: Any, *, key: str | None = None) -> Any:
    """Recursively redact credentials before durable experiment recording."""
    if key and _SECRET_KEY_PATTERN.search(str(key)):
        return "[REDACTED]"
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, dict):
        return {str(item_key): sanitize_for_ledger(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [sanitize_for_ledger(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_ledger(item) for item in value]
    return value


def _sanitize_command(command: str | None) -> tuple[str | None, str | None]:
    if not command:
        return None, None
    raw = str(command)
    return _sanitize_text(raw), hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _legacy_v1_present(root: Path) -> bool:
    ledger = _read_json_file(_paths(root)["ledger"], {})
    return isinstance(ledger, dict) and ledger.get("schema_version") == LEGACY_LEDGER_SCHEMA_VERSION


def _configure_connection(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    try:
        mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
        if str(mode).lower() != "wal":
            connection.execute("PRAGMA journal_mode = DELETE")
    except sqlite3.DatabaseError:
        connection.execute("PRAGMA journal_mode = DELETE")
    connection.execute("PRAGMA synchronous = FULL")


def _initialize_schema(connection: sqlite3.Connection, root: Path) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS ledger_meta (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            session_context_id TEXT PRIMARY KEY,
            project_root TEXT NOT NULL,
            working_directory TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('open','closed')),
            opened_at TEXT NOT NULL,
            touched_at TEXT NOT NULL,
            touched_epoch REAL NOT NULL,
            closed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS experiments (
            experiment_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            scientific_question TEXT,
            hypothesis TEXT,
            objective TEXT NOT NULL,
            stage TEXT NOT NULL,
            recipe TEXT,
            root_path TEXT NOT NULL,
            status TEXT NOT NULL,
            acceptance_criteria_json TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            current_iteration_id TEXT,
            next_action_json TEXT,
            conclusion TEXT,
            head_event_id TEXT,
            revision INTEGER NOT NULL DEFAULT 0,
            history_scope TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS experiment_edges (
            parent_experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
            child_experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
            relation TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(parent_experiment_id, child_experiment_id, relation)
        );
        CREATE TABLE IF NOT EXISTS iterations (
            iteration_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
            sequence INTEGER NOT NULL,
            parent_iteration_id TEXT,
            objective TEXT NOT NULL,
            status TEXT NOT NULL,
            acceptance_criteria_json TEXT NOT NULL,
            criterion_results_json TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            recovery_json TEXT,
            decision TEXT,
            next_action_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            UNIQUE(experiment_id, sequence)
        );
        CREATE TABLE IF NOT EXISTS activities (
            activity_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
            iteration_id TEXT REFERENCES iterations(iteration_id),
            started_session_context_id TEXT NOT NULL REFERENCES sessions(session_context_id),
            finished_session_context_id TEXT REFERENCES sessions(session_context_id),
            activity_type TEXT NOT NULL,
            objective TEXT NOT NULL,
            stage TEXT NOT NULL,
            status TEXT NOT NULL,
            protocol_json TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            expected_outputs_json TEXT NOT NULL,
            outputs_json TEXT NOT NULL,
            artifact_ids_json TEXT NOT NULL,
            job_ids_json TEXT NOT NULL,
            checkpoint_id TEXT,
            gate_ids_json TEXT NOT NULL,
            observations_json TEXT,
            metrics_json TEXT NOT NULL,
            failure_json TEXT,
            restart_from_json TEXT,
            next_action_json TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            experiment_id TEXT REFERENCES experiments(experiment_id),
            iteration_id TEXT REFERENCES iterations(iteration_id),
            activity_id TEXT REFERENCES activities(activity_id),
            session_context_id TEXT REFERENCES sessions(session_context_id),
            payload_json TEXT NOT NULL,
            event_hash TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS event_parents (
            event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
            parent_event_id TEXT NOT NULL REFERENCES events(event_id),
            parent_order INTEGER NOT NULL,
            PRIMARY KEY(event_id, parent_event_id)
        );
        CREATE TABLE IF NOT EXISTS references_log (
            reference_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
            experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
            iteration_id TEXT,
            activity_id TEXT,
            kind TEXT NOT NULL,
            target_id TEXT,
            path TEXT,
            sha256 TEXT,
            role TEXT NOT NULL,
            provenance TEXT,
            validation_status TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS handoffs (
            handoff_id TEXT PRIMARY KEY,
            session_context_id TEXT NOT NULL REFERENCES sessions(session_context_id),
            experiment_id TEXT REFERENCES experiments(experiment_id),
            summary_json TEXT NOT NULL,
            note_json TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_experiment_created ON events(experiment_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_activities_experiment_status ON activities(experiment_id, status);
        CREATE INDEX IF NOT EXISTS idx_iterations_experiment_sequence ON iterations(experiment_id, sequence);
        CREATE INDEX IF NOT EXISTS idx_refs_experiment_kind ON references_log(experiment_id, kind);
        CREATE TRIGGER IF NOT EXISTS events_no_update
        BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS events_no_delete
        BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS event_parents_no_update
        BEFORE UPDATE ON event_parents BEGIN SELECT RAISE(ABORT, 'event parents are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS event_parents_no_delete
        BEFORE DELETE ON event_parents BEGIN SELECT RAISE(ABORT, 'event parents are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS references_no_update
        BEFORE UPDATE ON references_log BEGIN SELECT RAISE(ABORT, 'references are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS references_no_delete
        BEFORE DELETE ON references_log BEGIN SELECT RAISE(ABORT, 'references are immutable'); END;
        """
    )
    now = _now_iso()
    defaults = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "history_mode": "forward_only",
        "history_start": None,
        "legacy_history_imported": False,
        "project_root": str(root),
        "created_at": now,
        "updated_at": now,
        "authoritative_store": DATABASE_FILE,
    }
    for key, value in defaults.items():
        connection.execute(
            "INSERT OR IGNORE INTO ledger_meta(key, value_json) VALUES (?, ?)",
            (key, _canonical_json(value)),
        )


def _connect(root: Path, *, create: bool = False, verify: bool = True) -> sqlite3.Connection | None:
    database = _paths(root)["database"]
    if not database.exists() and not create:
        return None
    database.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = sqlite3.connect(str(database), timeout=SQLITE_BUSY_TIMEOUT_MS / 1000, isolation_level=None)
        _configure_connection(connection)
        if create:
            _initialize_schema(connection, root)
        if verify:
            result = connection.execute("PRAGMA quick_check").fetchone()
            if not result or result[0] != "ok":
                raise LedgerCorruptionError(f"SQLite quick_check failed: {result[0] if result else 'no result'}")
            version_row = connection.execute(
                "SELECT value_json FROM ledger_meta WHERE key='schema_version'"
            ).fetchone()
            if not version_row:
                raise LedgerCorruptionError("Experiment ledger is missing schema_version")
            version = _json_load(version_row[0], None)
            if version != LEDGER_SCHEMA_VERSION:
                raise LedgerUpgradeRequired(f"Unsupported experiment ledger schema: {version}")
        return connection
    except (sqlite3.DatabaseError, OSError) as error:
        raise LedgerCorruptionError(f"Cannot open trusted experiment ledger {database}: {error}") from error


@contextlib.contextmanager
def _transaction(connection: sqlite3.Connection) -> Iterator[None]:
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield
        connection.execute("COMMIT")
    except Exception:
        with contextlib.suppress(sqlite3.DatabaseError):
            connection.execute("ROLLBACK")
        raise


def _meta(connection: sqlite3.Connection) -> dict[str, Any]:
    return {row["key"]: _json_load(row["value_json"], None) for row in connection.execute("SELECT key, value_json FROM ledger_meta")}


def _set_meta(connection: sqlite3.Connection, key: str, value: Any) -> None:
    connection.execute(
        "INSERT INTO ledger_meta(key, value_json) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
        (key, _canonical_json(value)),
    )


def ledger_status(project_root: str) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    paths = _paths(root)
    if not paths["database"].exists():
        if paths["ledger"].exists():
            legacy = _read_json_file(paths["ledger"], {}, strict=True)
            if not isinstance(legacy, dict):
                raise LedgerCorruptionError("Legacy experiment ledger must be a JSON object")
            if legacy.get("schema_version") != LEGACY_LEDGER_SCHEMA_VERSION:
                raise LedgerCorruptionError(
                    f"Unsupported legacy experiment ledger schema: {legacy.get('schema_version')}"
                )
            return {
                "status": "upgrade_required",
                "schema_version": LEGACY_LEDGER_SCHEMA_VERSION,
                "target_schema_version": LEDGER_SCHEMA_VERSION,
                "history_mode": "forward_only",
                "legacy_history_imported": False,
            }
        orphaned = [
            path.name for key, path in paths.items()
            if key not in {"base", "database", "ledger"} and path.exists() and path.stat().st_size > 0
        ]
        if orphaned:
            raise LedgerCorruptionError(
                f"Experiment memory exports exist without a canonical ledger: {sorted(orphaned)}"
            )
        return {
            "status": "not_started",
            "schema_version": LEDGER_SCHEMA_VERSION,
            "history_mode": "forward_only",
            "legacy_history_imported": False,
            "legacy_history_not_imported": True,
        }
    connection = _connect(root)
    assert connection is not None
    try:
        meta = _meta(connection)
        if meta.get("project_root") != str(root):
            raise LedgerCorruptionError(
                f"Experiment ledger project_root mismatch: {meta.get('project_root')} != {root}"
            )
        hash_failures = _verify_event_hashes(connection)
        if hash_failures:
            raise LedgerCorruptionError(
                f"Experiment ledger event hash verification failed for {len(hash_failures)} event(s)"
            )
    finally:
        connection.close()
    return {
        **meta,
        "status": "enabled" if meta.get("history_start") else "not_started",
        "legacy_history_not_imported": not bool(meta.get("legacy_history_imported")),
    }


def is_ledger_enabled(project_root: str) -> bool:
    return ledger_status(project_root).get("status") == "enabled"


def _row_experiment(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "experiment_id": row["experiment_id"],
        "title": row["title"],
        "scientific_question": row["scientific_question"],
        "hypothesis": row["hypothesis"],
        "objective": row["objective"],
        "stage": row["stage"],
        "recipe": row["recipe"],
        "root_path": row["root_path"],
        "status": row["status"],
        "acceptance_criteria": _json_load(row["acceptance_criteria_json"], []),
        "tags": _json_load(row["tags_json"], []),
        "current_iteration_id": row["current_iteration_id"],
        "next_action": _json_load(row["next_action_json"], None),
        "conclusion": row["conclusion"],
        "head_event_id": row["head_event_id"],
        "revision": row["revision"],
        "history_scope": row["history_scope"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "completed_at": row["completed_at"],
    }


def _row_iteration(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "iteration_id": row["iteration_id"],
        "experiment_id": row["experiment_id"],
        "sequence": row["sequence"],
        "parent_iteration_id": row["parent_iteration_id"],
        "objective": row["objective"],
        "status": row["status"],
        "acceptance_criteria": _json_load(row["acceptance_criteria_json"], []),
        "criterion_results": _json_load(row["criterion_results_json"], []),
        "inputs": _json_load(row["inputs_json"], []),
        "recovery": _json_load(row["recovery_json"], None),
        "decision": row["decision"],
        "next_action": _json_load(row["next_action_json"], None),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "completed_at": row["completed_at"],
    }


def _row_activity(row: sqlite3.Row) -> dict[str, Any]:
    protocol = _json_load(row["protocol_json"], {})
    return {
        "activity_id": row["activity_id"],
        "experiment_id": row["experiment_id"],
        "iteration_id": row["iteration_id"],
        "session_context_id": row["finished_session_context_id"] or row["started_session_context_id"],
        "started_session_context_id": row["started_session_context_id"],
        "finished_session_context_id": row["finished_session_context_id"],
        "activity_type": row["activity_type"],
        "objective": row["objective"],
        "stage": row["stage"],
        "status": row["status"],
        "protocol": protocol,
        "method": protocol.get("method"),
        "software": protocol.get("software"),
        "version": protocol.get("version"),
        "scripts": protocol.get("scripts", []),
        "command_redacted": protocol.get("command_redacted"),
        "command_sha256": protocol.get("command_sha256"),
        "parameters": protocol.get("parameters", {}),
        "inputs": _json_load(row["inputs_json"], []),
        "expected_outputs": _json_load(row["expected_outputs_json"], []),
        "outputs": _json_load(row["outputs_json"], []),
        "artifact_ids": _json_load(row["artifact_ids_json"], []),
        "job_ids": _json_load(row["job_ids_json"], []),
        "checkpoint_id": row["checkpoint_id"],
        "gate_ids": _json_load(row["gate_ids_json"], []),
        "observations": _json_load(row["observations_json"], None),
        "metrics": _json_load(row["metrics_json"], {}),
        "failure": _json_load(row["failure_json"], None),
        "restart_from": _json_load(row["restart_from_json"], None),
        "next_action": _json_load(row["next_action_json"], None),
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }


def _event_material(
    *,
    event_id: str,
    event_type: str,
    experiment_id: str | None,
    iteration_id: str | None,
    activity_id: str | None,
    session_context_id: str | None,
    payload: dict[str, Any],
    created_at: str,
    parent_hashes: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "event_id": event_id,
        "event_type": event_type,
        "experiment_id": experiment_id,
        "iteration_id": iteration_id,
        "activity_id": activity_id,
        "session_context_id": session_context_id,
        "payload": payload,
        "created_at": created_at,
        "parent_hashes": parent_hashes,
    }


def _append_event(
    connection: sqlite3.Connection,
    *,
    event_type: str,
    experiment_id: str | None,
    session_context_id: str | None,
    payload: dict[str, Any],
    iteration_id: str | None = None,
    activity_id: str | None = None,
    parent_event_ids: list[str] | None = None,
) -> dict[str, Any]:
    event_id = _id("evt")
    created_at = _now_iso()
    if parent_event_ids is None and experiment_id:
        row = connection.execute(
            "SELECT head_event_id FROM experiments WHERE experiment_id=?", (experiment_id,)
        ).fetchone()
        parent_event_ids = [row[0]] if row and row[0] else []
    parent_event_ids = list(dict.fromkeys(parent_event_ids or []))
    parent_hashes = []
    for parent_id in parent_event_ids:
        parent = connection.execute("SELECT event_hash FROM events WHERE event_id=?", (parent_id,)).fetchone()
        if not parent:
            raise ExperimentMemoryError(f"Unknown parent event: {parent_id}")
        parent_hashes.append(parent[0])
    clean_payload = sanitize_for_ledger(payload)
    material = _event_material(
        event_id=event_id,
        event_type=event_type,
        experiment_id=experiment_id,
        iteration_id=iteration_id,
        activity_id=activity_id,
        session_context_id=session_context_id,
        payload=clean_payload,
        created_at=created_at,
        parent_hashes=parent_hashes,
    )
    event_hash = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    connection.execute(
        "INSERT INTO events(event_id,event_type,experiment_id,iteration_id,activity_id,session_context_id,payload_json,event_hash,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            event_id,
            event_type,
            experiment_id,
            iteration_id,
            activity_id,
            session_context_id,
            _canonical_json(clean_payload),
            event_hash,
            created_at,
        ),
    )
    for index, parent_id in enumerate(parent_event_ids):
        connection.execute(
            "INSERT INTO event_parents(event_id,parent_event_id,parent_order) VALUES (?,?,?)",
            (event_id, parent_id, index),
        )
    if experiment_id:
        connection.execute(
            "UPDATE experiments SET head_event_id=?, revision=revision+1, updated_at=? WHERE experiment_id=?",
            (event_id, created_at, experiment_id),
        )
    _set_meta(connection, "updated_at", created_at)
    return {**material, "event_hash": event_hash}


def _event_record(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    parents = [
        value[0]
        for value in connection.execute(
            "SELECT parent_event_id FROM event_parents WHERE event_id=? ORDER BY parent_order", (row["event_id"],)
        )
    ]
    return {
        "event_id": row["event_id"],
        "event_type": row["event_type"],
        "experiment_id": row["experiment_id"],
        "iteration_id": row["iteration_id"],
        "activity_id": row["activity_id"],
        "session_context_id": row["session_context_id"],
        "payload": _json_load(row["payload_json"], {}),
        "event_hash": row["event_hash"],
        "parent_event_ids": parents,
        "created_at": row["created_at"],
    }


def _criteria(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if not isinstance(value, list):
        raise ExperimentMemoryError("acceptance_criteria must be an array")
    result = []
    seen: set[str] = set()
    for index, item in enumerate(value, start=1):
        if isinstance(item, str):
            item = {"description": item}
        if not isinstance(item, dict) or not str(item.get("description", "")).strip():
            raise ExperimentMemoryError("Each acceptance criterion requires a description")
        criterion_id = str(item.get("criterion_id") or f"criterion_{index:03d}")
        if criterion_id in seen:
            raise ExperimentMemoryError(f"Duplicate acceptance criterion: {criterion_id}")
        seen.add(criterion_id)
        result.append({"criterion_id": criterion_id, **sanitize_for_ledger(item)})
    return result


def _normalize_next_action(value: Any) -> dict[str, Any] | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        return {"action": _sanitize_text(value), "prerequisites": [], "approval_required": False}
    if not isinstance(value, dict) or not value.get("action"):
        raise ExperimentMemoryError("next_action must be a string or an object with action")
    return {
        "action": _sanitize_text(str(value["action"])),
        "prerequisites": sanitize_for_ledger(value.get("prerequisites") or []),
        "approval_required": bool(value.get("approval_required", False)),
        **({"gate": str(value["gate"])} if value.get("gate") else {}),
    }


def _normalize_scripts(root: Path, scripts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result = []
    for item in scripts or []:
        if not isinstance(item, dict) or not item.get("path"):
            raise ExperimentMemoryError("Each script reference requires path")
        path = resolve_project_path(str(item["path"]), project_root=str(root))
        if not path.is_file():
            raise ExperimentMemoryError(f"Script does not exist: {item['path']}")
        actual_hash = _file_sha256(path)
        expected_hash = item.get("sha256")
        if expected_hash and str(expected_hash) != actual_hash:
            raise ExperimentMemoryError(f"Script hash mismatch: {item['path']}")
        result.append({
            "path": str(path.relative_to(root)),
            "sha256": actual_hash,
            "role": str(item.get("role") or "script"),
        })
    return result


def _state_records(root: Path, state_file: str) -> list[dict[str, Any]]:
    value = _read_json_file(root / ".simflow" / "state" / state_file, [], strict=True)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict) and isinstance(value.get("decisions"), list):
        return [item for item in value["decisions"] if isinstance(item, dict)]
    return []


def _find_state_record(root: Path, kind: str, target_id: str) -> dict[str, Any] | None:
    mapping = {
        "artifact": ("artifacts.json", ("artifact_id",)),
        "checkpoint": ("checkpoints.json", ("checkpoint_id",)),
        "job": ("jobs.json", ("job_id",)),
        "gate": ("gates.json", ("gate_id", "decision_id")),
    }
    if kind not in mapping:
        return None
    state_file, keys = mapping[kind]
    for item in _state_records(root, state_file):
        if any(str(item.get(key, "")) == target_id for key in keys):
            return item
    return None


def _validate_reference(root: Path, reference: dict[str, Any], *, experiment_id: str, activity_id: str | None, strict_binding: bool) -> dict[str, Any]:
    if not isinstance(reference, dict):
        raise ExperimentMemoryError("Reference entries must be objects")
    kind = str(reference.get("kind") or "")
    if kind not in REFERENCE_KINDS:
        raise ExperimentMemoryError(f"Unsupported reference kind: {kind}")
    target_id = str(reference.get("id") or reference.get("target_id") or "") or None
    provenance = str(reference.get("provenance") or "current_experiment")
    if provenance not in {"current_experiment", "pre_ledger_baseline", "external"}:
        raise ExperimentMemoryError(f"Unsupported reference provenance: {provenance}")
    path_value = reference.get("path")
    actual_hash = None
    validation_status = "verified"
    metadata: dict[str, Any] = {}
    if kind == "path":
        if not path_value:
            raise ExperimentMemoryError("path reference requires path")
        path = resolve_project_path(str(path_value), project_root=str(root))
        if not path.exists():
            raise ExperimentMemoryError(f"Referenced path does not exist: {path_value}")
        actual_hash = _file_sha256(path) if path.is_file() else None
        path_value = str(path.relative_to(root))
    elif kind == "external":
        if not target_id and not path_value:
            raise ExperimentMemoryError("external reference requires id or path")
        validation_status = "declared_external"
    else:
        if not target_id:
            raise ExperimentMemoryError(f"{kind} reference requires id")
        record = _find_state_record(root, kind, target_id)
        if not record:
            raise ExperimentMemoryError(f"Unknown {kind} reference: {target_id}")
        metadata = {"record_status": record.get("status")}
        actual_hash = record.get("checksum") or record.get("script_hash") or record.get("input_artifact_hash")
        path_value = path_value or record.get("path")
        if strict_binding and provenance != "pre_ledger_baseline":
            if record.get("experiment_id") != experiment_id:
                raise ExperimentMemoryError(f"{kind} {target_id} is not linked to experiment {experiment_id}")
            if activity_id and record.get("activity_id") != activity_id:
                raise ExperimentMemoryError(f"{kind} {target_id} is not linked to activity {activity_id}")
    expected_hash = reference.get("sha256")
    if expected_hash and actual_hash and str(expected_hash) != str(actual_hash):
        raise ExperimentMemoryError(f"Reference hash mismatch for {target_id or path_value}")
    return {
        "kind": kind,
        "target_id": target_id,
        "path": path_value,
        "sha256": actual_hash or expected_hash,
        "role": str(reference.get("role") or "evidence"),
        "provenance": provenance,
        "validation_status": validation_status,
        "metadata": sanitize_for_ledger({**metadata, **(reference.get("metadata") or {})}),
    }


def _insert_references(
    connection: sqlite3.Connection,
    *,
    event_id: str,
    experiment_id: str,
    iteration_id: str | None,
    activity_id: str | None,
    references: list[dict[str, Any]],
) -> None:
    for item in references:
        connection.execute(
            "INSERT INTO references_log(reference_id,event_id,experiment_id,iteration_id,activity_id,kind,target_id,path,sha256,role,provenance,validation_status,metadata_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                _id("ref"), event_id, experiment_id, iteration_id, activity_id,
                item["kind"], item.get("target_id"), item.get("path"), item.get("sha256"),
                item["role"], item.get("provenance"), item["validation_status"],
                _canonical_json(item.get("metadata") or {}),
            ),
        )


def create_session_context(project_root: str, *, working_directory: str | None = None) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    status = ledger_status(str(root))
    if status.get("status") == "upgrade_required":
        raise LedgerUpgradeRequired("A v1 experiment ledger exists; call migrate_experiment_ledger explicitly")
    directory = resolve_project_path(working_directory or str(root), project_root=str(root))
    connection = _connect(root, create=True)
    assert connection is not None
    context_id = _id("ctx")
    now = _now_iso()
    try:
        with _transaction(connection):
            connection.execute(
                "INSERT INTO sessions(session_context_id,project_root,working_directory,status,opened_at,touched_at,touched_epoch,closed_at) "
                "VALUES (?,?,?,?,?,?,?,NULL)",
                (context_id, str(root), str(directory), "open", now, now, _now_epoch()),
            )
    finally:
        connection.close()
    export_memory_views(str(root))
    return {
        "event": "opened",
        "session_context_id": context_id,
        "project_root": str(root),
        "working_directory": str(directory),
        "ts": now,
        "_ts_epoch": _now_epoch(),
    }


def _validate_session_row(connection: sqlite3.Connection, session_context_id: str, *, touch: bool) -> sqlite3.Row:
    if not session_context_id:
        raise ExperimentMemoryError("session_context_id is required; call project_reentry first")
    row = connection.execute(
        "SELECT * FROM sessions WHERE session_context_id=?", (session_context_id,)
    ).fetchone()
    if not row:
        raise ExperimentMemoryError("Unknown session_context_id; call project_reentry again")
    if row["status"] == "closed":
        raise ExperimentMemoryError("session_context_id is closed; call project_reentry again")
    if _now_epoch() - float(row["touched_epoch"]) > SESSION_TIMEOUT_SECONDS:
        raise ExperimentMemoryError("session_context_id expired; call project_reentry again")
    if touch:
        now = _now_iso()
        connection.execute(
            "UPDATE sessions SET touched_at=?, touched_epoch=? WHERE session_context_id=?",
            (now, _now_epoch(), session_context_id),
        )
        row = connection.execute("SELECT * FROM sessions WHERE session_context_id=?", (session_context_id,)).fetchone()
    return row


def validate_session_context(project_root: str, session_context_id: str, *, touch: bool = False) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment session store exists; call project_reentry first")
    try:
        with _transaction(connection) if touch else contextlib.nullcontext():
            row = _validate_session_row(connection, session_context_id, touch=touch)
        return {
            "event": "touched" if touch else "opened",
            "session_context_id": row["session_context_id"],
            "project_root": row["project_root"],
            "working_directory": row["working_directory"],
            "ts": row["touched_at"],
            "_ts_epoch": row["touched_epoch"],
        }
    finally:
        connection.close()


def close_session_context(project_root: str, session_context_id: str) -> None:
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment session store exists")
    try:
        with _transaction(connection):
            _validate_session_row(connection, session_context_id, touch=False)
            now = _now_iso()
            connection.execute(
                "UPDATE sessions SET status='closed', closed_at=?, touched_at=?, touched_epoch=? WHERE session_context_id=?",
                (now, now, _now_epoch(), session_context_id),
            )
    finally:
        connection.close()
    export_memory_views(str(root))


def _context_from_environment(root: Path) -> ExperimentContext | None:
    values = {field: os.environ.get(env_name) for field, env_name in CONTEXT_ENV.items()}
    if not any(values.values()):
        return None
    missing = [field for field in ("session_context_id", "experiment_id", "activity_id") if not values.get(field)]
    if missing:
        raise ExperimentMemoryError(f"Incomplete SimFlow experiment context environment; missing {missing}")
    return ExperimentContext(project_root=str(root), **values)  # type: ignore[arg-type]


def _context_from_values(
    root: Path,
    *,
    session_context_id: str | None,
    experiment_id: str | None,
    iteration_id: str | None,
    activity_id: str | None,
) -> ExperimentContext | None:
    provided = [session_context_id, experiment_id, activity_id, iteration_id]
    if not any(provided):
        return None
    missing = [
        name for name, value in (
            ("session_context_id", session_context_id),
            ("experiment_id", experiment_id),
            ("activity_id", activity_id),
        ) if not value
    ]
    if missing:
        raise ExperimentMemoryError(f"Incomplete experiment context; missing {missing}")
    return ExperimentContext(
        project_root=str(root),
        session_context_id=str(session_context_id),
        experiment_id=str(experiment_id),
        iteration_id=str(iteration_id) if iteration_id else None,
        activity_id=str(activity_id),
    )


def current_experiment_context(project_root: str | None = None) -> ExperimentContext | None:
    context = _ACTIVE_CONTEXT.get()
    if not context:
        return None
    if project_root:
        root = resolve_project_root(project_root=project_root)
        if Path(context.project_root) != root:
            raise ExperimentMemoryError("Active experiment context belongs to a different project_root")
    return context


def require_write_context(
    project_root: str,
    *,
    session_context_id: str | None = None,
    experiment_id: str | None = None,
    iteration_id: str | None = None,
    activity_id: str | None = None,
) -> ExperimentContext | None:
    """Return a verified write context, or fail closed when the ledger is enabled."""
    root = resolve_project_root(project_root=project_root)
    status = ledger_status(str(root))
    if status.get("status") != "enabled":
        return None
    ambient = current_experiment_context(str(root)) or _context_from_environment(root)
    explicit_values = (session_context_id, experiment_id, iteration_id, activity_id)
    explicit = None
    if any(explicit_values):
        explicit = _context_from_values(
            root,
            session_context_id=session_context_id or (ambient.session_context_id if ambient else None),
            experiment_id=experiment_id or (ambient.experiment_id if ambient else None),
            iteration_id=iteration_id if iteration_id is not None else (ambient.iteration_id if ambient else None),
            activity_id=activity_id or (ambient.activity_id if ambient else None),
        )
    context = explicit or ambient
    if not context:
        raise ExperimentMemoryError(
            "The experiment ledger is enabled; provide session_context_id, experiment_id, and activity_id"
        )
    validate_activity_binding(
        str(root),
        session_context_id=context.session_context_id,
        experiment_id=context.experiment_id,
        activity_id=context.activity_id,
        iteration_id=context.iteration_id,
    )
    return context


@contextlib.contextmanager
def experiment_write_scope(context: ExperimentContext | None) -> Iterator[ExperimentContext | None]:
    token = _ACTIVE_CONTEXT.set(context)
    previous_env = {name: os.environ.get(name) for name in CONTEXT_ENV.values()}
    try:
        if context:
            os.environ.update(context.environment())
        yield context
    finally:
        _ACTIVE_CONTEXT.reset(token)
        for name, value in previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def activate_write_context(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    activity_id: str,
    iteration_id: str | None = None,
) -> contextlib.AbstractContextManager[ExperimentContext | None]:
    context = require_write_context(
        project_root,
        session_context_id=session_context_id,
        experiment_id=experiment_id,
        iteration_id=iteration_id,
        activity_id=activity_id,
    )
    return experiment_write_scope(context)


def begin_experiment(
    project_root: str,
    *,
    session_context_id: str,
    title: str,
    objective: str,
    stage: str,
    root_path: str,
    recipe: str | None = None,
    acceptance_criteria: Any = None,
    next_action: Any = None,
    scientific_question: str | None = None,
    hypothesis: str | None = None,
    tags: list[str] | None = None,
    parent_experiment_ids: list[str] | None = None,
    baseline_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    experiment_path = resolve_project_path(root_path, project_root=str(root))
    connection = _connect(root, create=True)
    assert connection is not None
    experiment_id = _id("exp")
    now = _now_iso()
    criteria = _criteria(acceptance_criteria)
    clean_next = _normalize_next_action(next_action)
    parents = list(dict.fromkeys(parent_experiment_ids or []))
    references = [
        _validate_reference(root, item, experiment_id=experiment_id, activity_id=None, strict_binding=False)
        for item in (baseline_refs or [])
    ]
    try:
        with _transaction(connection):
            _validate_session_row(connection, session_context_id, touch=True)
            for parent_id in parents:
                if not connection.execute("SELECT 1 FROM experiments WHERE experiment_id=?", (parent_id,)).fetchone():
                    raise ExperimentMemoryError(f"Unknown parent experiment: {parent_id}")
            meta = _meta(connection)
            if not meta.get("history_start"):
                _set_meta(connection, "history_start", now)
            connection.execute(
                "INSERT INTO experiments(experiment_id,title,scientific_question,hypothesis,objective,stage,recipe,root_path,status,acceptance_criteria_json,tags_json,current_iteration_id,next_action_json,conclusion,head_event_id,revision,history_scope,created_at,updated_at,completed_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,0,?,?,?,NULL)",
                (
                    experiment_id, _sanitize_text(title), _sanitize_text(scientific_question) if scientific_question else None,
                    _sanitize_text(hypothesis) if hypothesis else None, _sanitize_text(objective), stage, recipe,
                    str(experiment_path.relative_to(root)) if experiment_path != root else ".", "active",
                    _canonical_json(criteria), _canonical_json(sorted(set(tags or []))), None,
                    _canonical_json(clean_next) if clean_next else None, None,
                    "from_experiment_creation_only", now, now,
                ),
            )
            for parent_id in parents:
                connection.execute(
                    "INSERT INTO experiment_edges(parent_experiment_id,child_experiment_id,relation,created_at) VALUES (?,?,?,?)",
                    (parent_id, experiment_id, "forked_from", now),
                )
            event = _append_event(
                connection,
                event_type="experiment_started",
                experiment_id=experiment_id,
                session_context_id=session_context_id,
                payload={
                    "title": title,
                    "scientific_question": scientific_question,
                    "hypothesis": hypothesis,
                    "objective": objective,
                    "stage": stage,
                    "recipe": recipe,
                    "root_path": str(experiment_path.relative_to(root)) if experiment_path != root else ".",
                    "acceptance_criteria": criteria,
                    "tags": sorted(set(tags or [])),
                    "parent_experiment_ids": parents,
                    "baseline_refs": references,
                    "next_action": clean_next,
                },
                parent_event_ids=[],
            )
            _insert_references(
                connection,
                event_id=event["event_id"],
                experiment_id=experiment_id,
                iteration_id=None,
                activity_id=None,
                references=references,
            )
            row = connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
    finally:
        connection.close()
    export_memory_views(str(root))
    return _row_experiment(row)


def fork_experiment(
    project_root: str,
    *,
    session_context_id: str,
    parent_experiment_id: str,
    title: str,
    objective: str,
    root_path: str,
    scientific_question: str | None = None,
    hypothesis: str | None = None,
    stage: str | None = None,
    recipe: str | None = None,
    acceptance_criteria: Any = None,
    baseline_refs: list[dict[str, Any]] | None = None,
    next_action: Any = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment ledger exists")
    try:
        parent = connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (parent_experiment_id,)).fetchone()
        if not parent:
            raise ExperimentMemoryError(f"Unknown parent experiment: {parent_experiment_id}")
        parent_value = _row_experiment(parent)
    finally:
        connection.close()
    return begin_experiment(
        str(root),
        session_context_id=session_context_id,
        title=title,
        scientific_question=scientific_question or parent_value.get("scientific_question"),
        hypothesis=hypothesis,
        objective=objective,
        stage=stage or parent_value["stage"],
        recipe=recipe or parent_value.get("recipe"),
        root_path=root_path,
        acceptance_criteria=acceptance_criteria,
        parent_experiment_ids=[parent_experiment_id],
        baseline_refs=baseline_refs,
        next_action=next_action,
    )


def finish_experiment(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    status: str,
    conclusion: str | None = None,
    next_action: Any = None,
) -> dict[str, Any]:
    if status not in EXPERIMENT_STATUSES - {"active"}:
        raise ExperimentMemoryError(f"Unsupported terminal experiment status: {status}")
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment ledger exists")
    now = _now_iso()
    clean_next = _normalize_next_action(next_action)
    try:
        with _transaction(connection):
            _validate_session_row(connection, session_context_id, touch=True)
            current = connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
            if not current:
                raise ExperimentMemoryError(f"Unknown experiment: {experiment_id}")
            if current["status"] in EXPERIMENT_TERMINAL_STATUSES:
                raise ExperimentMemoryError("experiment_id is already terminal")
            running = connection.execute(
                "SELECT activity_id FROM activities WHERE experiment_id=? AND status='running'", (experiment_id,)
            ).fetchall()
            if running:
                raise ExperimentMemoryError("Cannot finish experiment while activities are running")
            open_iterations = connection.execute(
                "SELECT iteration_id,status FROM iterations WHERE experiment_id=? AND status IN ('running','evaluating')",
                (experiment_id,),
            ).fetchall()
            if open_iterations:
                raise ExperimentMemoryError("Cannot finish experiment while an iteration is running or evaluating")
            completed_at = now if status in EXPERIMENT_TERMINAL_STATUSES else None
            connection.execute(
                "UPDATE experiments SET status=?, conclusion=?, next_action_json=?, completed_at=?, updated_at=? WHERE experiment_id=?",
                (
                    status,
                    _sanitize_text(conclusion) if conclusion else None,
                    _canonical_json(clean_next) if clean_next else None,
                    completed_at,
                    now,
                    experiment_id,
                ),
            )
            _append_event(
                connection,
                event_type="experiment_status_changed",
                experiment_id=experiment_id,
                session_context_id=session_context_id,
                payload={"status": status, "conclusion": conclusion, "next_action": clean_next},
            )
            row = connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
    finally:
        connection.close()
    export_memory_views(str(root))
    return _row_experiment(row)


def resume_experiment(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    next_action: Any = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment ledger exists")
    clean_next = _normalize_next_action(next_action)
    try:
        with _transaction(connection):
            _validate_session_row(connection, session_context_id, touch=True)
            row = connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
            if not row:
                raise ExperimentMemoryError(f"Unknown experiment: {experiment_id}")
            if row["status"] != "paused":
                raise ExperimentMemoryError("Only paused experiments can be resumed")
            connection.execute(
                "UPDATE experiments SET status='active', next_action_json=?, completed_at=NULL WHERE experiment_id=?",
                (_canonical_json(clean_next) if clean_next else row["next_action_json"], experiment_id),
            )
            _append_event(
                connection,
                event_type="experiment_resumed",
                experiment_id=experiment_id,
                session_context_id=session_context_id,
                payload={"next_action": clean_next},
            )
            row = connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
    finally:
        connection.close()
    export_memory_views(str(root))
    return _row_experiment(row)


def begin_iteration(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    objective: str,
    acceptance_criteria: Any,
    parent_iteration_id: str | None = None,
    inputs: list[Any] | None = None,
    next_action: Any = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment ledger exists")
    criteria = _criteria(acceptance_criteria)
    if not criteria:
        raise ExperimentMemoryError("An iteration requires at least one acceptance criterion")
    clean_next = _normalize_next_action(next_action)
    iteration_id = _id("iter")
    now = _now_iso()
    try:
        with _transaction(connection):
            _validate_session_row(connection, session_context_id, touch=True)
            experiment = connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
            if not experiment:
                raise ExperimentMemoryError(f"Unknown experiment: {experiment_id}")
            if experiment["status"] != "active":
                raise ExperimentMemoryError("Iterations can start only on an active experiment")
            if connection.execute(
                "SELECT 1 FROM iterations WHERE experiment_id=? AND status IN ('running','evaluating','paused')",
                (experiment_id,),
            ).fetchone():
                raise ExperimentMemoryError("The experiment already has an open iteration")
            if parent_iteration_id:
                parent = connection.execute(
                    "SELECT * FROM iterations WHERE iteration_id=? AND experiment_id=?",
                    (parent_iteration_id, experiment_id),
                ).fetchone()
                if not parent:
                    raise ExperimentMemoryError(f"Unknown parent iteration: {parent_iteration_id}")
                if parent["status"] not in ITERATION_TERMINAL_STATUSES:
                    raise ExperimentMemoryError("parent_iteration_id must be terminal")
            sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM iterations WHERE experiment_id=?", (experiment_id,)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO iterations(iteration_id,experiment_id,sequence,parent_iteration_id,objective,status,acceptance_criteria_json,criterion_results_json,inputs_json,recovery_json,decision,next_action_json,created_at,updated_at,completed_at) "
                "VALUES (?,?,?,?,?,'running',?,?,?,NULL,NULL,?,?,?,NULL)",
                (
                    iteration_id, experiment_id, sequence, parent_iteration_id, _sanitize_text(objective),
                    _canonical_json(criteria), _canonical_json([]), _canonical_json(sanitize_for_ledger(inputs or [])),
                    _canonical_json(clean_next) if clean_next else None, now, now,
                ),
            )
            connection.execute(
                "UPDATE experiments SET current_iteration_id=?, next_action_json=? WHERE experiment_id=?",
                (iteration_id, _canonical_json(clean_next) if clean_next else None, experiment_id),
            )
            _append_event(
                connection,
                event_type="iteration_started",
                experiment_id=experiment_id,
                iteration_id=iteration_id,
                session_context_id=session_context_id,
                payload={
                    "sequence": sequence,
                    "parent_iteration_id": parent_iteration_id,
                    "objective": objective,
                    "acceptance_criteria": criteria,
                    "inputs": inputs or [],
                    "next_action": clean_next,
                },
            )
            row = connection.execute("SELECT * FROM iterations WHERE iteration_id=?", (iteration_id,)).fetchone()
    finally:
        connection.close()
    export_memory_views(str(root))
    return _row_iteration(row)


def evaluate_iteration(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    iteration_id: str,
    status: str,
    criterion_results: list[dict[str, Any]] | None,
    decision: str,
    next_action: Any = None,
    recovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in ITERATION_STATUSES - {"running"}:
        raise ExperimentMemoryError(f"Unsupported iteration evaluation status: {status}")
    if not str(decision or "").strip():
        raise ExperimentMemoryError("decision is required")
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment ledger exists")
    clean_results = sanitize_for_ledger(criterion_results or [])
    clean_next = _normalize_next_action(next_action)
    clean_recovery = sanitize_for_ledger(recovery) if recovery else None
    recovery_references = _recovery_references(
        root,
        experiment_id=experiment_id,
        activity_id=None,
        recovery=clean_recovery,
    )
    now = _now_iso()
    try:
        with _transaction(connection):
            _validate_session_row(connection, session_context_id, touch=True)
            iteration = connection.execute(
                "SELECT * FROM iterations WHERE iteration_id=? AND experiment_id=?", (iteration_id, experiment_id)
            ).fetchone()
            if not iteration:
                raise ExperimentMemoryError("iteration_id does not belong to experiment_id")
            if iteration["status"] in ITERATION_TERMINAL_STATUSES:
                raise ExperimentMemoryError("iteration_id is already terminal")
            criteria = _json_load(iteration["acceptance_criteria_json"], [])
            if status == "accepted":
                expected = {item["criterion_id"] for item in criteria}
                received = {
                    str(item.get("criterion_id"))
                    for item in clean_results
                    if isinstance(item, dict) and str(item.get("status", "")).lower() in {"pass", "passed", "met"}
                }
                if expected != received:
                    raise ExperimentMemoryError("accepted iteration requires a passing result for every acceptance criterion")
            completed_at = now if status in ITERATION_TERMINAL_STATUSES else None
            connection.execute(
                "UPDATE iterations SET status=?,criterion_results_json=?,recovery_json=?,decision=?,next_action_json=?,updated_at=?,completed_at=? WHERE iteration_id=?",
                (
                    status, _canonical_json(clean_results), _canonical_json(clean_recovery) if clean_recovery else None,
                    _sanitize_text(decision), _canonical_json(clean_next) if clean_next else None,
                    now, completed_at, iteration_id,
                ),
            )
            connection.execute(
                "UPDATE experiments SET next_action_json=? WHERE experiment_id=?",
                (_canonical_json(clean_next) if clean_next else None, experiment_id),
            )
            event = _append_event(
                connection,
                event_type="iteration_evaluated",
                experiment_id=experiment_id,
                iteration_id=iteration_id,
                session_context_id=session_context_id,
                payload={
                    "status": status,
                    "criterion_results": clean_results,
                    "decision": decision,
                    "recovery": clean_recovery,
                    "next_action": clean_next,
                },
            )
            _insert_references(
                connection,
                event_id=event["event_id"],
                experiment_id=experiment_id,
                iteration_id=iteration_id,
                activity_id=None,
                references=recovery_references,
            )
            row = connection.execute("SELECT * FROM iterations WHERE iteration_id=?", (iteration_id,)).fetchone()
    finally:
        connection.close()
    export_memory_views(str(root))
    return _row_iteration(row)


def start_activity(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    objective: str,
    activity_type: str,
    stage: str,
    iteration_id: str | None = None,
    method: str | None = None,
    software: str | None = None,
    version: str | None = None,
    scripts: list[dict[str, Any]] | None = None,
    command: str | None = None,
    inputs: list[Any] | None = None,
    parameters: dict[str, Any] | None = None,
    expected_outputs: list[Any] | None = None,
    gate_ids: list[str] | None = None,
    random_seeds: list[Any] | None = None,
    environment_ref: str | None = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No enabled experiment ledger exists; call begin_experiment first")
    activity_id = _id("act")
    now = _now_iso()
    command_redacted, command_sha256 = _sanitize_command(command)
    clean_scripts = _normalize_scripts(root, scripts)
    clean_gates = list(dict.fromkeys(str(value) for value in (gate_ids or [])))
    for gate_id in clean_gates:
        _validate_reference(
            root,
            {"kind": "gate", "id": gate_id, "role": "approval"},
            experiment_id=experiment_id,
            activity_id=None,
            strict_binding=False,
        )
    protocol = sanitize_for_ledger({
        "method": method,
        "software": software,
        "version": version,
        "scripts": clean_scripts,
        "command_redacted": command_redacted,
        "command_sha256": command_sha256,
        "parameters": parameters or {},
        "random_seeds": random_seeds or [],
        "environment_ref": environment_ref,
    })
    try:
        with _transaction(connection):
            _validate_session_row(connection, session_context_id, touch=True)
            experiment = connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
            if not experiment:
                raise ExperimentMemoryError(f"Unknown experiment: {experiment_id}")
            if experiment["status"] != "active":
                raise ExperimentMemoryError("Activities can start only on an active experiment")
            if iteration_id:
                iteration = connection.execute(
                    "SELECT * FROM iterations WHERE iteration_id=? AND experiment_id=?", (iteration_id, experiment_id)
                ).fetchone()
                if not iteration:
                    raise ExperimentMemoryError("iteration_id does not belong to experiment_id")
                if iteration["status"] not in {"running", "evaluating"}:
                    raise ExperimentMemoryError("Activities require a running or evaluating iteration")
            connection.execute(
                "INSERT INTO activities(activity_id,experiment_id,iteration_id,started_session_context_id,finished_session_context_id,activity_type,objective,stage,status,protocol_json,inputs_json,expected_outputs_json,outputs_json,artifact_ids_json,job_ids_json,checkpoint_id,gate_ids_json,observations_json,metrics_json,failure_json,restart_from_json,next_action_json,started_at,finished_at) "
                "VALUES (?,?,?,?,NULL,?,?,?,'running',?,?,?,?,?,?,NULL,?,NULL,?,NULL,NULL,NULL,?,NULL)",
                (
                    activity_id, experiment_id, iteration_id, session_context_id, activity_type,
                    _sanitize_text(objective), stage, _canonical_json(protocol),
                    _canonical_json(sanitize_for_ledger(inputs or [])),
                    _canonical_json(sanitize_for_ledger(expected_outputs or [])),
                    _canonical_json([]), _canonical_json([]), _canonical_json([]),
                    _canonical_json(clean_gates), _canonical_json({}), now,
                ),
            )
            event = _append_event(
                connection,
                event_type="activity_started",
                experiment_id=experiment_id,
                iteration_id=iteration_id,
                activity_id=activity_id,
                session_context_id=session_context_id,
                payload={
                    "activity_type": activity_type,
                    "objective": objective,
                    "stage": stage,
                    "protocol": protocol,
                    "inputs": inputs or [],
                    "expected_outputs": expected_outputs or [],
                    "gate_ids": clean_gates,
                },
            )
            row = connection.execute("SELECT * FROM activities WHERE activity_id=?", (activity_id,)).fetchone()
    finally:
        connection.close()
    export_memory_views(str(root))
    result = _row_activity(row)
    context = ExperimentContext(str(root), session_context_id, experiment_id, activity_id, iteration_id)
    result["context"] = context.as_dict()
    result["environment"] = context.environment()
    result["event_id"] = event["event_id"]
    result["event_hash"] = event["event_hash"]
    return result


def validate_activity_binding(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    activity_id: str,
    iteration_id: str | None = None,
    touch: bool = True,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment ledger exists")
    try:
        with _transaction(connection) if touch else contextlib.nullcontext():
            _validate_session_row(connection, session_context_id, touch=touch)
            experiment = connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
            if not experiment:
                raise ExperimentMemoryError(f"Unknown experiment: {experiment_id}")
            if experiment["status"] != "active":
                raise ExperimentMemoryError("experiment_id is not active")
            activity = connection.execute(
                "SELECT * FROM activities WHERE activity_id=? AND experiment_id=?", (activity_id, experiment_id)
            ).fetchone()
            if not activity:
                raise ExperimentMemoryError("activity_id does not belong to experiment_id")
            if activity["status"] != "running":
                raise ExperimentMemoryError("activity_id is not active")
            if iteration_id is not None and activity["iteration_id"] != iteration_id:
                raise ExperimentMemoryError("activity_id does not belong to iteration_id")
            return _row_activity(activity)
    finally:
        connection.close()


def _strict_activity_references(
    root: Path,
    *,
    experiment_id: str,
    activity_id: str,
    artifact_ids: list[str],
    job_ids: list[str],
    checkpoint_id: str | None,
    output_paths: list[Any],
) -> list[dict[str, Any]]:
    refs = []
    for artifact_id in artifact_ids:
        refs.append(_validate_reference(
            root, {"kind": "artifact", "id": artifact_id, "role": "output"},
            experiment_id=experiment_id, activity_id=activity_id, strict_binding=True,
        ))
    for job_id in job_ids:
        refs.append(_validate_reference(
            root, {"kind": "job", "id": job_id, "role": "execution"},
            experiment_id=experiment_id, activity_id=activity_id, strict_binding=True,
        ))
    if checkpoint_id:
        refs.append(_validate_reference(
            root, {"kind": "checkpoint", "id": checkpoint_id, "role": "checkpoint"},
            experiment_id=experiment_id, activity_id=activity_id, strict_binding=True,
        ))
    for value in output_paths:
        if isinstance(value, str):
            refs.append(_validate_reference(
                root, {"kind": "path", "path": value, "role": "output"},
                experiment_id=experiment_id, activity_id=activity_id, strict_binding=False,
            ))
        elif isinstance(value, dict) and value.get("path"):
            refs.append(_validate_reference(
                root, {"kind": "path", "role": "output", **value},
                experiment_id=experiment_id, activity_id=activity_id, strict_binding=False,
            ))
    return refs


def _recovery_references(
    root: Path,
    *,
    experiment_id: str,
    activity_id: str | None,
    recovery: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not recovery:
        return []
    if not isinstance(recovery, dict):
        raise ExperimentMemoryError("recovery/restart_from must be an object")
    provenance = str(recovery.get("provenance") or "current_experiment")
    references = []
    for key, kind in (("checkpoint_id", "checkpoint"), ("artifact_id", "artifact"), ("job_id", "job")):
        if recovery.get(key):
            references.append(_validate_reference(
                root,
                {"kind": kind, "id": recovery[key], "role": "recovery", "provenance": provenance},
                experiment_id=experiment_id,
                activity_id=activity_id,
                strict_binding=True,
            ))
    if recovery.get("path"):
        references.append(_validate_reference(
            root,
            {"kind": "path", "path": recovery["path"], "role": "recovery", "provenance": provenance},
            experiment_id=experiment_id,
            activity_id=activity_id,
            strict_binding=False,
        ))
    if not references:
        raise ExperimentMemoryError("recovery/restart_from requires checkpoint_id, artifact_id, job_id, or path")
    return references


def finish_activity(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    activity_id: str,
    status: str,
    outputs: list[Any] | None = None,
    artifact_ids: list[str] | None = None,
    job_ids: list[str] | None = None,
    checkpoint_id: str | None = None,
    observations: Any = None,
    metrics: dict[str, Any] | None = None,
    failure: dict[str, Any] | None = None,
    restart_from: dict[str, Any] | None = None,
    next_action: Any = None,
) -> dict[str, Any]:
    if status not in ACTIVITY_TERMINAL_STATUSES:
        raise ExperimentMemoryError(f"Unsupported activity terminal status: {status}")
    if status == "failed" and not failure:
        raise ExperimentMemoryError("failed activity requires failure details")
    root = resolve_project_root(project_root=project_root)
    clean_artifacts = list(dict.fromkeys(str(value) for value in (artifact_ids or [])))
    clean_jobs = list(dict.fromkeys(str(value) for value in (job_ids or [])))
    clean_outputs = sanitize_for_ledger(outputs or [])
    clean_next = _normalize_next_action(next_action)
    references = _strict_activity_references(
        root,
        experiment_id=experiment_id,
        activity_id=activity_id,
        artifact_ids=clean_artifacts,
        job_ids=clean_jobs,
        checkpoint_id=checkpoint_id,
        output_paths=clean_outputs,
    )
    clean_restart = sanitize_for_ledger(restart_from) if restart_from else None
    references.extend(_recovery_references(
        root,
        experiment_id=experiment_id,
        activity_id=activity_id,
        recovery=clean_restart,
    ))
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment ledger exists")
    now = _now_iso()
    try:
        with _transaction(connection):
            _validate_session_row(connection, session_context_id, touch=True)
            activity = connection.execute(
                "SELECT * FROM activities WHERE activity_id=? AND experiment_id=?", (activity_id, experiment_id)
            ).fetchone()
            if not activity:
                raise ExperimentMemoryError("activity_id does not belong to experiment_id")
            if activity["status"] != "running":
                raise ExperimentMemoryError("activity_id is already finished")
            connection.execute(
                "UPDATE activities SET finished_session_context_id=?,status=?,outputs_json=?,artifact_ids_json=?,job_ids_json=?,checkpoint_id=?,observations_json=?,metrics_json=?,failure_json=?,restart_from_json=?,next_action_json=?,finished_at=? WHERE activity_id=?",
                (
                    session_context_id, status, _canonical_json(clean_outputs), _canonical_json(clean_artifacts),
                    _canonical_json(clean_jobs), checkpoint_id,
                    _canonical_json(sanitize_for_ledger(observations)) if observations is not None else None,
                    _canonical_json(sanitize_for_ledger(metrics or {})),
                    _canonical_json(sanitize_for_ledger(failure)) if failure else None,
                    _canonical_json(clean_restart) if clean_restart else None,
                    _canonical_json(clean_next) if clean_next else None,
                    now, activity_id,
                ),
            )
            connection.execute(
                "UPDATE experiments SET next_action_json=? WHERE experiment_id=?",
                (_canonical_json(clean_next) if clean_next else None, experiment_id),
            )
            if activity["iteration_id"] and clean_restart:
                connection.execute(
                    "UPDATE iterations SET recovery_json=?,next_action_json=?,updated_at=? WHERE iteration_id=?",
                    (_canonical_json(clean_restart), _canonical_json(clean_next) if clean_next else None, now, activity["iteration_id"]),
                )
            event = _append_event(
                connection,
                event_type="activity_finished",
                experiment_id=experiment_id,
                iteration_id=activity["iteration_id"],
                activity_id=activity_id,
                session_context_id=session_context_id,
                payload={
                    "status": status,
                    "outputs": clean_outputs,
                    "artifact_ids": clean_artifacts,
                    "job_ids": clean_jobs,
                    "checkpoint_id": checkpoint_id,
                    "observations": observations,
                    "metrics": metrics or {},
                    "failure": failure,
                    "restart_from": clean_restart,
                    "next_action": clean_next,
                },
            )
            _insert_references(
                connection,
                event_id=event["event_id"],
                experiment_id=experiment_id,
                iteration_id=activity["iteration_id"],
                activity_id=activity_id,
                references=references,
            )
            row = connection.execute("SELECT * FROM activities WHERE activity_id=?", (activity_id,)).fetchone()
    finally:
        connection.close()
    export_memory_views(str(root))
    result = _row_activity(row)
    result["event_id"] = event["event_id"]
    result["event_hash"] = event["event_hash"]
    return result


def record_linked_write(
    project_root: str,
    *,
    kind: str,
    target_id: str | None = None,
    path: str | None = None,
    sha256: str | None = None,
    role: str = "state_write",
    metadata: dict[str, Any] | None = None,
    session_context_id: str | None = None,
    experiment_id: str | None = None,
    iteration_id: str | None = None,
    activity_id: str | None = None,
) -> dict[str, Any] | None:
    """Attach a successful core write to the currently active experiment activity."""
    root = resolve_project_root(project_root=project_root)
    context = require_write_context(
        str(root),
        session_context_id=session_context_id,
        experiment_id=experiment_id,
        iteration_id=iteration_id,
        activity_id=activity_id,
    )
    if not context:
        return None
    reference = _validate_reference(
        root,
        {"kind": kind, "id": target_id, "path": path, "sha256": sha256, "role": role, "metadata": metadata or {}},
        experiment_id=context.experiment_id,
        activity_id=context.activity_id,
        strict_binding=kind in {"artifact", "checkpoint", "job", "gate"},
    )
    connection = _connect(root)
    assert connection is not None
    try:
        with _transaction(connection):
            event = _append_event(
                connection,
                event_type=f"{kind}_linked",
                experiment_id=context.experiment_id,
                iteration_id=context.iteration_id,
                activity_id=context.activity_id,
                session_context_id=context.session_context_id,
                payload={"reference": reference},
            )
            _insert_references(
                connection,
                event_id=event["event_id"],
                experiment_id=context.experiment_id,
                iteration_id=context.iteration_id,
                activity_id=context.activity_id,
                references=[reference],
            )
        return event
    finally:
        connection.close()


def _select_experiment(
    root: Path,
    experiments: list[dict[str, Any]],
    *,
    experiment_id: str | None,
    working_directory: str | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str | None]:
    active = [item for item in experiments if item.get("status") in {"active", "paused"}]
    if experiment_id:
        selected = next((item for item in experiments if item["experiment_id"] == experiment_id), None)
        if not selected:
            raise ExperimentMemoryError(f"Unknown experiment: {experiment_id}")
        return selected, active, None
    if working_directory:
        current = resolve_project_path(working_directory, project_root=str(root))
        matches = []
        for item in active:
            path = resolve_project_path(item.get("root_path") or ".", project_root=str(root))
            try:
                current.relative_to(path)
            except ValueError:
                continue
            matches.append((len(path.parts), item))
        if matches:
            longest = max(length for length, _ in matches)
            best = [item for length, item in matches if length == longest]
            if len(best) == 1:
                return best[0], active, None
            return None, active, "multiple_active_experiments_same_root"
    if len(active) == 1:
        return active[0], active, None
    if len(active) > 1:
        return None, active, "multiple_active_experiments"
    return None, active, None


def _latest_checkpoint(root: Path, experiment_id: str, *, successful: bool) -> dict[str, Any] | None:
    records = _state_records(root, "checkpoints.json")
    matches = [item for item in records if item.get("experiment_id") == experiment_id]
    if successful:
        matches = [item for item in matches if item.get("status") == "success" and item.get("recoverable", True)]
    if not matches:
        return None
    item = dict(matches[-1])
    checkpoint_path = item.get("path")
    if checkpoint_path:
        stored = _read_json_file(root / str(checkpoint_path), {}, strict=True)
        if isinstance(stored, dict):
            item = {**item, **stored}
    return {
        key: item.get(key)
        for key in (
            "checkpoint_id", "stage_id", "job_id", "experiment_id", "iteration_id",
            "activity_id", "description", "status", "recoverable", "created_at",
        )
    }


def _references_for_experiment(connection: sqlite3.Connection, experiment_id: str) -> list[dict[str, Any]]:
    return [
        {
            "reference_id": row["reference_id"],
            "event_id": row["event_id"],
            "kind": row["kind"],
            "target_id": row["target_id"],
            "path": row["path"],
            "sha256": row["sha256"],
            "role": row["role"],
            "provenance": row["provenance"],
            "validation_status": row["validation_status"],
            "metadata": _json_load(row["metadata_json"], {}),
        }
        for row in connection.execute(
            "SELECT * FROM references_log WHERE experiment_id=? ORDER BY rowid", (experiment_id,)
        )
    ]


def build_reentry_summary(
    project_root: str,
    *,
    experiment_id: str | None = None,
    working_directory: str | None = None,
    recent_limit: int = 10,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    status = ledger_status(str(root))
    if status.get("status") in {"not_started", "upgrade_required"}:
        return {
            "status": "success",
            "project_root": str(root),
            "ledger": status,
            "selection_required": False,
            "selection_reason": None,
            "active_experiments": [],
            "selected_experiment": None,
            "current_iteration": None,
            "interrupted_activities": [],
            "latest_completed_activity": None,
            "latest_failure": None,
            "latest_event_checkpoint": None,
            "latest_successful_checkpoint": None,
            "latest_recovery": None,
            "recent_events": [],
            "next_action": None,
            "integrity": {"status": "not_started", "head_event_ids": [], "event_count": 0},
            "legacy_state_policy": "Legacy .simflow/state remains queryable but never determines experiment selection, recovery, or next_action.",
        }
    connection = _connect(root)
    assert connection is not None
    try:
        experiments = [_row_experiment(row) for row in connection.execute("SELECT * FROM experiments ORDER BY created_at")]
        selected, active, selection_reason = _select_experiment(
            root, experiments, experiment_id=experiment_id, working_directory=working_directory
        )
        selected_iterations: list[dict[str, Any]] = []
        selected_activities: list[dict[str, Any]] = []
        recent_events: list[dict[str, Any]] = []
        references: list[dict[str, Any]] = []
        if selected:
            selected_iterations = [
                _row_iteration(row)
                for row in connection.execute(
                    "SELECT * FROM iterations WHERE experiment_id=? ORDER BY sequence", (selected["experiment_id"],)
                )
            ]
            selected_activities = [
                _row_activity(row)
                for row in connection.execute(
                    "SELECT * FROM activities WHERE experiment_id=? ORDER BY started_at", (selected["experiment_id"],)
                )
            ]
            event_rows = connection.execute(
                "SELECT * FROM events WHERE experiment_id=? ORDER BY created_at,event_id DESC LIMIT ?",
                (selected["experiment_id"], max(1, min(int(recent_limit), 50))),
            ).fetchall()
            recent_events = [_event_record(connection, row) for row in reversed(event_rows)]
            references = _references_for_experiment(connection, selected["experiment_id"])
        current_iteration = None
        if selected and selected.get("current_iteration_id"):
            current_iteration = next(
                (item for item in selected_iterations if item["iteration_id"] == selected["current_iteration_id"]), None
            )
        interrupted = [item for item in selected_activities if item["status"] == "running"]
        terminal = sorted(
            [item for item in selected_activities if item["status"] != "running"],
            key=lambda item: item.get("finished_at") or item.get("started_at") or "",
        )
        completed = [item for item in terminal if item["status"] in {"completed", "partial"}]
        failures = [item for item in terminal if item["status"] == "failed"]
        event_count = connection.execute(
            "SELECT COUNT(*) FROM events WHERE experiment_id=?", ((selected or {}).get("experiment_id"),)
        ).fetchone()[0] if selected else 0
        parents = []
        children = []
        if selected:
            parents = [row[0] for row in connection.execute(
                "SELECT parent_experiment_id FROM experiment_edges WHERE child_experiment_id=?", (selected["experiment_id"],)
            )]
            children = [row[0] for row in connection.execute(
                "SELECT child_experiment_id FROM experiment_edges WHERE parent_experiment_id=?", (selected["experiment_id"],)
            )]
            selected = {**selected, "parent_experiment_ids": parents, "child_experiment_ids": children}
        latest_event_checkpoint = _latest_checkpoint(root, selected["experiment_id"], successful=False) if selected else None
        latest_successful_checkpoint = _latest_checkpoint(root, selected["experiment_id"], successful=True) if selected else None
        explicit_recovery = (current_iteration or {}).get("recovery")
        next_action_detail = (current_iteration or {}).get("next_action") or (selected or {}).get("next_action")
        next_action = next_action_detail.get("action") if isinstance(next_action_detail, dict) else next_action_detail
        return {
            "status": "success",
            "project_root": str(root),
            "ledger": status,
            "selection_required": selection_reason is not None,
            "selection_reason": selection_reason,
            "active_experiments": [
                {key: item.get(key) for key in ("experiment_id", "title", "root_path", "status", "current_iteration_id", "next_action", "revision")}
                for item in active
            ],
            "selected_experiment": selected,
            "current_iteration": current_iteration,
            "iterations": selected_iterations,
            "activities": selected_activities,
            "interrupted_activities": interrupted,
            "latest_completed_activity": completed[-1] if completed else None,
            "latest_failure": failures[-1] if failures else None,
            "latest_event_checkpoint": latest_event_checkpoint,
            "latest_successful_checkpoint": latest_successful_checkpoint,
            "latest_recovery": explicit_recovery or latest_successful_checkpoint,
            "recent_events": recent_events,
            "references": references[-50:],
            "next_action": next_action,
            "next_action_detail": next_action_detail,
            "integrity": {
                "status": "verified",
                "head_event_ids": [selected["head_event_id"]] if selected and selected.get("head_event_id") else [],
                "event_count": event_count,
                "revision": (selected or {}).get("revision", 0),
            },
            "legacy_state_policy": "Legacy .simflow/state remains queryable but never determines experiment selection, recovery, or next_action.",
        }
    finally:
        connection.close()


def project_reentry(
    project_root: str,
    *,
    experiment_id: str | None = None,
    working_directory: str | None = None,
    recent_limit: int = 10,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    if _legacy_v1_present(root) and not _paths(root)["database"].exists():
        summary = build_reentry_summary(str(root), experiment_id=experiment_id, working_directory=working_directory, recent_limit=recent_limit)
        summary["session_context_id"] = None
        return summary
    context = create_session_context(str(root), working_directory=working_directory)
    summary = build_reentry_summary(
        str(root), experiment_id=experiment_id, working_directory=working_directory, recent_limit=recent_limit
    )
    summary["session_context_id"] = context["session_context_id"]
    return summary


def experiment_timeline(
    project_root: str,
    *,
    experiment_id: str,
    iteration_id: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
    include_events: bool = False,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment ledger exists")
    try:
        experiment_row = connection.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
        if not experiment_row:
            raise ExperimentMemoryError(f"Unknown experiment: {experiment_id}")
        query = "SELECT * FROM activities WHERE experiment_id=?"
        values: list[Any] = [experiment_id]
        if iteration_id:
            query += " AND iteration_id=?"
            values.append(iteration_id)
        if status:
            query += " AND status=?"
            values.append(status)
        query += " ORDER BY started_at LIMIT ? OFFSET ?"
        page_limit = max(1, min(int(limit), 200))
        values.extend([page_limit, max(offset, 0)])
        activities = [_row_activity(row) for row in connection.execute(query, values)]
        count_query = "SELECT COUNT(*) FROM activities WHERE experiment_id=?"
        count_values: list[Any] = [experiment_id]
        if iteration_id:
            count_query += " AND iteration_id=?"
            count_values.append(iteration_id)
        if status:
            count_query += " AND status=?"
            count_values.append(status)
        events = []
        if include_events:
            events = [
                _event_record(connection, row)
                for row in connection.execute(
                    "SELECT * FROM events WHERE experiment_id=? ORDER BY created_at LIMIT ? OFFSET ?",
                    (experiment_id, page_limit, max(offset, 0)),
                )
            ]
        return {
            "status": "success",
            "project_root": str(root),
            "experiment": _row_experiment(experiment_row),
            "iterations": [_row_iteration(row) for row in connection.execute(
                "SELECT * FROM iterations WHERE experiment_id=? ORDER BY sequence", (experiment_id,)
            )],
            "activities": activities,
            "events": events,
            "total": connection.execute(count_query, count_values).fetchone()[0],
            "offset": max(offset, 0),
            "limit": page_limit,
        }
    finally:
        connection.close()


def compare_experiments(project_root: str, *, experiment_ids: list[str]) -> dict[str, Any]:
    if len(experiment_ids) < 2 or len(experiment_ids) > 10:
        raise ExperimentMemoryError("compare_experiments requires 2-10 experiment_ids")
    summaries = [build_reentry_summary(project_root, experiment_id=value) for value in experiment_ids]
    comparison = []
    for summary in summaries:
        experiment = summary["selected_experiment"]
        activity = summary.get("latest_completed_activity") or summary.get("latest_failure") or {}
        comparison.append({
            "experiment_id": experiment["experiment_id"],
            "title": experiment["title"],
            "status": experiment["status"],
            "revision": experiment["revision"],
            "current_iteration": (summary.get("current_iteration") or {}).get("sequence"),
            "latest_metrics": activity.get("metrics") or {},
            "latest_failure": (summary.get("latest_failure") or {}).get("failure"),
            "recovery_checkpoint_id": (summary.get("latest_successful_checkpoint") or {}).get("checkpoint_id"),
            "next_action": summary.get("next_action"),
            "parent_experiment_ids": experiment.get("parent_experiment_ids", []),
        })
    return {"status": "success", "project_root": str(resolve_project_root(project_root=project_root)), "experiments": comparison}


def _verify_event_hashes(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    failures = []
    for row in connection.execute("SELECT * FROM events ORDER BY created_at,event_id"):
        parent_rows = connection.execute(
            "SELECT e.event_hash FROM event_parents p JOIN events e ON e.event_id=p.parent_event_id "
            "WHERE p.event_id=? ORDER BY p.parent_order",
            (row["event_id"],),
        ).fetchall()
        material = _event_material(
            event_id=row["event_id"], event_type=row["event_type"], experiment_id=row["experiment_id"],
            iteration_id=row["iteration_id"], activity_id=row["activity_id"],
            session_context_id=row["session_context_id"], payload=_json_load(row["payload_json"], {}),
            created_at=row["created_at"], parent_hashes=[item[0] for item in parent_rows],
        )
        actual = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
        if actual != row["event_hash"]:
            failures.append({"event_id": row["event_id"], "expected": row["event_hash"], "actual": actual})
    return failures


def verify_experiment_ledger(project_root: str, *, verify_references: bool = True) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root, verify=False)
    if connection is None:
        return {"status": "not_started", "project_root": str(root)}
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        hash_failures = _verify_event_hashes(connection) if integrity == "ok" else []
        reference_failures = []
        if verify_references and integrity == "ok":
            for row in connection.execute("SELECT * FROM references_log ORDER BY rowid"):
                try:
                    _validate_reference(
                        root,
                        {
                            "kind": row["kind"], "id": row["target_id"], "path": row["path"],
                            "sha256": row["sha256"], "role": row["role"], "provenance": row["provenance"],
                        },
                        experiment_id=row["experiment_id"], activity_id=row["activity_id"],
                        strict_binding=row["kind"] in {"artifact", "checkpoint", "job", "gate"} and bool(row["activity_id"]),
                    )
                except Exception as error:
                    reference_failures.append({"reference_id": row["reference_id"], "error": str(error)})
        status = "verified" if integrity == "ok" and not hash_failures and not reference_failures else "corrupt"
        return {
            "status": status,
            "project_root": str(root),
            "sqlite_integrity": integrity,
            "event_hash_failures": hash_failures,
            "reference_failures": reference_failures,
            "event_count": connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            "experiment_count": connection.execute("SELECT COUNT(*) FROM experiments").fetchone()[0],
        }
    finally:
        connection.close()


def session_handoff(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        raise ExperimentMemoryError("No experiment ledger exists")
    summary = build_reentry_summary(str(root), experiment_id=experiment_id)
    handoff_id = _id("handoff")
    created_at = _now_iso()
    handoff = {
        "handoff_id": handoff_id,
        "session_context_id": session_context_id,
        "experiment_id": (summary.get("selected_experiment") or {}).get("experiment_id"),
        "current_iteration_id": (summary.get("current_iteration") or {}).get("iteration_id"),
        "interrupted_activity_ids": [item.get("activity_id") for item in summary.get("interrupted_activities", [])],
        "latest_completed_activity_id": (summary.get("latest_completed_activity") or {}).get("activity_id"),
        "latest_failure_activity_id": (summary.get("latest_failure") or {}).get("activity_id"),
        "latest_event_checkpoint_id": (summary.get("latest_event_checkpoint") or {}).get("checkpoint_id"),
        "latest_recovery_checkpoint_id": (summary.get("latest_successful_checkpoint") or {}).get("checkpoint_id"),
        "latest_recovery": summary.get("latest_recovery"),
        "next_action": summary.get("next_action"),
        "integrity": summary.get("integrity"),
        "note": sanitize_for_ledger(note),
        "created_at": created_at,
    }
    try:
        with _transaction(connection):
            _validate_session_row(connection, session_context_id, touch=False)
            selected_id = handoff["experiment_id"]
            if selected_id:
                _append_event(
                    connection,
                    event_type="session_handoff_created",
                    experiment_id=selected_id,
                    iteration_id=handoff["current_iteration_id"],
                    session_context_id=session_context_id,
                    payload=handoff,
                )
            connection.execute(
                "INSERT INTO handoffs(handoff_id,session_context_id,experiment_id,summary_json,note_json,created_at) VALUES (?,?,?,?,?,?)",
                (
                    handoff_id, session_context_id, selected_id, _canonical_json(handoff),
                    _canonical_json(sanitize_for_ledger(note)) if note else None, created_at,
                ),
            )
            connection.execute(
                "UPDATE sessions SET status='closed',closed_at=?,touched_at=?,touched_epoch=? WHERE session_context_id=?",
                (created_at, created_at, _now_epoch(), session_context_id),
            )
    finally:
        connection.close()
    export_memory_views(str(root))
    _write_handoff_report(root, handoff)
    return handoff


def _write_handoff_report(root: Path, handoff: dict[str, Any]) -> Path:
    report = root / ".simflow" / "reports" / f"session_handoff_{handoff['handoff_id']}.md"
    lines = [
        f"# Experiment Session Handoff - {handoff['handoff_id']}", "",
        f"- Experiment ID: {handoff.get('experiment_id') or 'unselected'}",
        f"- Current iteration: {handoff.get('current_iteration_id') or 'none'}",
        f"- Latest completed activity: {handoff.get('latest_completed_activity_id') or 'none'}",
        f"- Latest failure activity: {handoff.get('latest_failure_activity_id') or 'none'}",
        f"- Latest event checkpoint: {handoff.get('latest_event_checkpoint_id') or 'none'}",
        f"- Latest successful recovery checkpoint: {handoff.get('latest_recovery_checkpoint_id') or 'none'}",
        f"- Interrupted activities: {', '.join(value for value in handoff.get('interrupted_activity_ids', []) if value) or 'none'}",
        f"- Next action: {_canonical_json(handoff.get('next_action')) if handoff.get('next_action') else 'unspecified'}",
        f"- Integrity: {(handoff.get('integrity') or {}).get('status', 'unknown')}",
        f"- Note: {handoff.get('note') or 'none'}", "",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def _experiment_notebook_lines(summary: dict[str, Any]) -> list[str]:
    experiment = summary["selected_experiment"]
    iteration = summary.get("current_iteration") or {}
    latest = summary.get("latest_completed_activity") or {}
    failure = summary.get("latest_failure") or {}
    lines = [
        f"# {experiment.get('title', experiment['experiment_id'])}", "",
        f"- Experiment ID: {experiment['experiment_id']}",
        f"- Status: {experiment.get('status')}",
        f"- Scientific question: {experiment.get('scientific_question') or 'unspecified'}",
        f"- Hypothesis: {experiment.get('hypothesis') or 'unspecified'}",
        f"- Objective: {experiment.get('objective')}",
        f"- Stage / recipe: {experiment.get('stage')} / {experiment.get('recipe') or 'unspecified'}",
        f"- Root path: {experiment.get('root_path')}",
        f"- Parents: {', '.join(experiment.get('parent_experiment_ids', [])) or 'none'}",
        f"- Revision: {experiment.get('revision')}",
        f"- Integrity head: {experiment.get('head_event_id') or 'none'}", "",
        "## Current Iteration", "",
        f"- Iteration: {iteration.get('iteration_id') or 'none'}",
        f"- Status: {iteration.get('status') or 'none'}",
        f"- Objective: {iteration.get('objective') or 'none'}",
        f"- Decision: {iteration.get('decision') or 'none'}",
        f"- Recovery: {_canonical_json(summary.get('latest_recovery')) if summary.get('latest_recovery') else 'none'}", "",
        "## Latest Result", "",
        f"- Activity: {latest.get('activity_id') or 'none'}",
        f"- Metrics: {_canonical_json(latest.get('metrics') or {})}",
        f"- Artifacts: {', '.join(latest.get('artifact_ids') or []) or 'none'}", "",
        "## Latest Failure", "",
        f"- Activity: {failure.get('activity_id') or 'none'}",
        f"- Failure: {_canonical_json(failure.get('failure')) if failure.get('failure') else 'none'}", "",
        "## Next Action", "",
        _canonical_json(summary.get("next_action")) if summary.get("next_action") else "unspecified", "",
        "## Iteration History", "",
    ]
    for item in summary.get("iterations", []):
        lines.append(
            f"- {item['iteration_id']} | {item['status']} | {item['objective']} | decision: {item.get('decision') or 'none'}"
        )
    lines.extend(["", "## Activity History", ""])
    for item in summary.get("activities", []):
        protocol = item.get("protocol") or {}
        lines.extend([
            f"### {item['activity_id']} - {item.get('objective')}", "",
            f"- Status: {item.get('status')}",
            f"- Type / stage: {item.get('activity_type')} / {item.get('stage')}",
            f"- Iteration: {item.get('iteration_id') or 'none'}",
            f"- Method: {protocol.get('method') or 'unspecified'}",
            f"- Software: {protocol.get('software') or 'unspecified'} {protocol.get('version') or ''}".rstrip(),
            f"- Scripts: {_canonical_json(protocol.get('scripts') or [])}",
            f"- Parameters: {_canonical_json(protocol.get('parameters') or {})}",
            f"- Inputs: {_canonical_json(item.get('inputs') or [])}",
            f"- Outputs: {_canonical_json(item.get('outputs') or [])}",
            f"- Artifacts: {', '.join(item.get('artifact_ids') or []) or 'none'}",
            f"- Jobs: {', '.join(item.get('job_ids') or []) or 'none'}",
            f"- Checkpoint: {item.get('checkpoint_id') or 'none'}",
            f"- Metrics: {_canonical_json(item.get('metrics') or {})}",
            f"- Failure: {_canonical_json(item.get('failure')) if item.get('failure') else 'none'}",
            f"- Restart from: {_canonical_json(item.get('restart_from')) if item.get('restart_from') else 'none'}",
            f"- Next action: {_canonical_json(item.get('next_action')) if item.get('next_action') else 'none'}", "",
        ])
    lines.extend(["", "## Recent Events", ""])
    for event in summary.get("recent_events", []):
        lines.append(f"- {event['created_at']} | {event['event_type']} | {event['event_id']} | {event['event_hash'][:12]}")
    return lines


def render_experiment_notebook(project_root: str, experiment_id: str) -> Path:
    root = resolve_project_root(project_root=project_root)
    summary = build_reentry_summary(str(root), experiment_id=experiment_id, recent_limit=50)
    if not summary.get("selected_experiment"):
        raise ExperimentMemoryError(f"Unknown experiment: {experiment_id}")
    report = root / ".simflow" / "reports" / "experiments" / f"{experiment_id}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(_experiment_notebook_lines(summary)) + "\n", encoding="utf-8")
    return report


@contextlib.contextmanager
def _export_lock(root: Path) -> Iterator[None]:
    lock_path = _paths(root)["base"] / ".export.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def export_memory_views(project_root: str) -> dict[str, str]:
    root = resolve_project_root(project_root=project_root)
    with _export_lock(root):
        return _export_memory_views_unlocked(str(root))


def _export_memory_views_unlocked(project_root: str) -> dict[str, str]:
    """Regenerate human-readable and JSON compatibility views from SQLite."""
    root = resolve_project_root(project_root=project_root)
    connection = _connect(root)
    if connection is None:
        return {}
    paths = _paths(root)
    try:
        meta = _meta(connection)
        experiments = [_row_experiment(row) for row in connection.execute("SELECT * FROM experiments ORDER BY created_at")]
        iterations = [_row_iteration(row) for row in connection.execute("SELECT * FROM iterations ORDER BY created_at")]
        activities = [_row_activity(row) for row in connection.execute("SELECT * FROM activities ORDER BY started_at")]
        sessions = [
            {
                "session_context_id": row["session_context_id"], "project_root": row["project_root"],
                "working_directory": row["working_directory"], "status": row["status"],
                "opened_at": row["opened_at"], "touched_at": row["touched_at"], "closed_at": row["closed_at"],
            }
            for row in connection.execute("SELECT * FROM sessions ORDER BY opened_at")
        ]
        handoffs = [_json_load(row["summary_json"], {}) for row in connection.execute("SELECT summary_json FROM handoffs ORDER BY created_at")]
        events = [_event_record(connection, row) for row in connection.execute("SELECT * FROM events ORDER BY created_at,event_id")]
        ledger = {
            **meta,
            "status": "enabled" if meta.get("history_start") else "not_started",
            "authoritative_store": DATABASE_FILE,
            "exports_are_authoritative": False,
        }
        summary = {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "status": ledger["status"],
            "project_root": str(root),
            "experiment_count": len(experiments),
            "active_experiment_ids": [item["experiment_id"] for item in experiments if item["status"] in {"active", "paused"}],
            "event_count": len(events),
            "updated_at": meta.get("updated_at"),
            "integrity": "unverified_export",
        }
    finally:
        connection.close()
    _write_json_atomic(paths["ledger"], ledger)
    _write_json_atomic(paths["experiments"], experiments)
    _write_json_atomic(paths["iterations"], iterations)
    _write_jsonl_atomic(paths["activities"], activities)
    _write_jsonl_atomic(paths["contexts"], sessions)
    _write_jsonl_atomic(paths["handoffs"], handoffs)
    _write_jsonl_atomic(paths["events"], events)
    _write_json_atomic(paths["summary"], summary)
    for experiment in experiments:
        render_experiment_notebook(str(root), experiment["experiment_id"])
    return {name: str(path.relative_to(root)) for name, path in paths.items() if name not in {"base", "database"}}


def rebuild_experiment_exports(
    project_root: str,
    *,
    session_context_id: str,
    experiment_id: str,
    activity_id: str,
    iteration_id: str | None = None,
) -> dict[str, Any]:
    context = require_write_context(
        project_root,
        session_context_id=session_context_id,
        experiment_id=experiment_id,
        iteration_id=iteration_id,
        activity_id=activity_id,
    )
    with experiment_write_scope(context):
        outputs = export_memory_views(project_root)
    return {"status": "success", "project_root": str(resolve_project_root(project_root=project_root)), "outputs": outputs}


def migrate_experiment_ledger(project_root: str, *, confirm: bool = False) -> dict[str, Any]:
    """Explicitly migrate only structured v1 ledger records; never host transcripts."""
    if not confirm:
        raise ExperimentMemoryError("confirm=true is required for v1 structured-ledger migration")
    root = resolve_project_root(project_root=project_root)
    paths = _paths(root)
    if paths["database"].exists():
        raise ExperimentMemoryError("A v2 experiment ledger already exists")
    ledger = _read_json_file(paths["ledger"], {}, strict=True)
    if ledger.get("schema_version") != LEGACY_LEDGER_SCHEMA_VERSION:
        raise ExperimentMemoryError("No v1 structured experiment ledger found")
    experiments = _read_json_file(paths["experiments"], [], strict=True)
    iterations = _read_json_file(paths["iterations"], [], strict=True)
    activities = _read_jsonl_file(paths["activities"])
    contexts = _read_jsonl_file(paths["contexts"])
    handoffs = _read_jsonl_file(paths["handoffs"])
    archive = paths["base"] / "v1_archive"
    archive.mkdir(parents=True, exist_ok=False)
    for name in ("ledger", "experiments", "iterations", "activities", "contexts", "handoffs"):
        source = paths[name]
        if source.exists():
            source.replace(archive / source.name)
    connection = _connect(root, create=True)
    assert connection is not None
    imported = {"experiments": 0, "iterations": 0, "activities": 0, "handoffs": 0}
    try:
        with _transaction(connection):
            _set_meta(connection, "history_start", ledger.get("history_start") or _now_iso())
            _set_meta(connection, "migrated_from", LEGACY_LEDGER_SCHEMA_VERSION)
            for context in contexts:
                context_id = context.get("session_context_id")
                if not context_id:
                    continue
                event = context.get("event")
                connection.execute(
                    "INSERT OR IGNORE INTO sessions(session_context_id,project_root,working_directory,status,opened_at,touched_at,touched_epoch,closed_at) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        context_id, str(root), context.get("working_directory") or str(root),
                        "closed" if event == "closed" else "open", context.get("ts") or _now_iso(),
                        context.get("ts") or _now_iso(), float(context.get("_ts_epoch") or _now_epoch()),
                        context.get("ts") if event == "closed" else None,
                    ),
                )
            migration_session = next((item.get("session_context_id") for item in contexts if item.get("session_context_id")), None)
            if not migration_session:
                migration_session = _id("ctx")
                now = _now_iso()
                connection.execute(
                    "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)",
                    (migration_session, str(root), str(root), "closed", now, now, _now_epoch(), now),
                )
            for item in experiments:
                experiment_id = item["experiment_id"]
                connection.execute(
                    "INSERT INTO experiments(experiment_id,title,scientific_question,hypothesis,objective,stage,recipe,root_path,status,acceptance_criteria_json,tags_json,current_iteration_id,next_action_json,conclusion,head_event_id,revision,history_scope,created_at,updated_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,0,?,?,?,?)",
                    (
                        experiment_id, item.get("title") or experiment_id, None, None, item.get("objective") or "migrated v1 experiment",
                        item.get("stage") or "computation", item.get("recipe"), item.get("root_path") or ".",
                        item.get("status") or "paused", _canonical_json(item.get("acceptance_criteria") or []),
                        _canonical_json([]), item.get("current_iteration_id"),
                        _canonical_json(_normalize_next_action(item.get("next_action"))) if item.get("next_action") else None,
                        item.get("conclusion"), item.get("history_scope") or "from_experiment_creation_only",
                        item.get("created_at") or _now_iso(), item.get("updated_at") or _now_iso(), item.get("completed_at"),
                    ),
                )
                _append_event(
                    connection, event_type="v1_experiment_migrated", experiment_id=experiment_id,
                    session_context_id=migration_session, payload=item, parent_event_ids=[],
                )
                imported["experiments"] += 1
            for item in iterations:
                connection.execute(
                    "INSERT INTO iterations(iteration_id,experiment_id,sequence,parent_iteration_id,objective,status,acceptance_criteria_json,criterion_results_json,inputs_json,recovery_json,decision,next_action_json,created_at,updated_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        item["iteration_id"], item["experiment_id"], item.get("sequence") or 1,
                        item.get("parent_iteration_id"), item.get("objective") or "migrated v1 iteration",
                        item.get("status") or "paused", _canonical_json(item.get("acceptance_criteria") or []),
                        _canonical_json(item.get("criterion_results") or []), _canonical_json(item.get("inputs") or []),
                        _canonical_json(item.get("recovery")) if item.get("recovery") else None, item.get("decision"),
                        _canonical_json(_normalize_next_action(item.get("next_action"))) if item.get("next_action") else None,
                        item.get("created_at") or _now_iso(), item.get("updated_at") or _now_iso(), item.get("completed_at"),
                    ),
                )
                imported["iterations"] += 1
            for item in activities:
                context_id = item.get("session_context_id") or migration_session
                activity_id = item["activity_id"]
                protocol = {
                    key: item.get(key)
                    for key in ("method", "software", "version", "scripts", "command_redacted", "command_sha256", "parameters")
                }
                connection.execute(
                    "INSERT INTO activities(activity_id,experiment_id,iteration_id,started_session_context_id,finished_session_context_id,activity_type,objective,stage,status,protocol_json,inputs_json,expected_outputs_json,outputs_json,artifact_ids_json,job_ids_json,checkpoint_id,gate_ids_json,observations_json,metrics_json,failure_json,restart_from_json,next_action_json,started_at,finished_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        activity_id, item["experiment_id"], item.get("iteration_id"), context_id,
                        context_id if item.get("status") != "running" else None, item.get("activity_type") or "migrated",
                        item.get("objective") or "migrated v1 activity", item.get("stage") or "computation",
                        item.get("status") or "paused", _canonical_json(protocol), _canonical_json(item.get("inputs") or []),
                        _canonical_json(item.get("expected_outputs") or []), _canonical_json(item.get("outputs") or []),
                        _canonical_json(item.get("artifact_ids") or []), _canonical_json(item.get("job_ids") or []),
                        item.get("checkpoint_id"), _canonical_json(item.get("gate_ids") or []),
                        _canonical_json(item.get("observations")) if item.get("observations") is not None else None,
                        _canonical_json(item.get("metrics") or {}), _canonical_json(item.get("failure")) if item.get("failure") else None,
                        _canonical_json(item.get("restart_from")) if item.get("restart_from") else None,
                        _canonical_json(_normalize_next_action(item.get("next_action"))) if item.get("next_action") else None,
                        item.get("started_at") or _now_iso(), item.get("finished_at"),
                    ),
                )
                _append_event(
                    connection, event_type="v1_activity_migrated", experiment_id=item["experiment_id"],
                    iteration_id=item.get("iteration_id"), activity_id=activity_id,
                    session_context_id=context_id, payload=item,
                )
                imported["activities"] += 1
            for item in handoffs:
                handoff_id = item.get("handoff_id") or _id("handoff")
                context_id = item.get("session_context_id") or migration_session
                connection.execute(
                    "INSERT INTO handoffs VALUES (?,?,?,?,?,?)",
                    (handoff_id, context_id, item.get("experiment_id"), _canonical_json(item), None, item.get("created_at") or _now_iso()),
                )
                imported["handoffs"] += 1
    except Exception:
        connection.close()
        paths["database"].unlink(missing_ok=True)
        for source in archive.iterdir():
            source.replace(paths["base"] / source.name)
        archive.rmdir()
        raise
    else:
        connection.close()
    export_memory_views(str(root))
    return {"status": "success", "project_root": str(root), "imported": imported, "archive": str(archive.relative_to(root))}
