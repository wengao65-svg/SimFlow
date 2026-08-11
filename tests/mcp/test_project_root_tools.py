#!/usr/bin/env python3
"""Project-root boundary tests for the four compact state tools."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT / "mcp" / "servers" / "simflow_state" / "tools"


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(f"compact_{name}_tool", TOOLS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_record_and_inspect_use_explicit_project_root_without_touching_omx(tmp_path):
    record = _load_tool("record")
    inspect = _load_tool("inspect")
    host_file = tmp_path / ".omx" / "session.json"
    host_file.parent.mkdir()
    host_file.write_text('{"owner":"host"}\n', encoding="utf-8")

    written = record.execute({
        "project_root": str(tmp_path),
        "kind": "artifact",
        "summary": "logical output",
    })
    loaded = inspect.execute({"project_root": str(tmp_path)})

    assert written["status"] == "success"
    assert loaded["data"]["record_count"] == 1
    assert (tmp_path / ".simflow" / "records.jsonl").is_file()
    assert host_file.read_text(encoding="utf-8") == '{"owner":"host"}\n'


def test_checkpoint_and_recover_use_project_root(tmp_path):
    checkpoint = _load_tool("checkpoint")
    recover = _load_tool("recover")
    restart = tmp_path / "restart.dat"
    restart.write_text("restart\n", encoding="utf-8")

    created = checkpoint.execute({
        "project_root": str(tmp_path),
        "summary": "resume point",
        "restart_refs": ["restart.dat"],
        "resume_command": "solver restart.dat",
    })
    loaded = recover.execute({
        "project_root": str(tmp_path),
        "checkpoint_id": created["data"]["checkpoint_id"],
    })

    assert created["status"] == "success"
    assert loaded["status"] == "success"
    assert loaded["data"]["ready"] is True


def test_all_compact_tools_reject_missing_project_root():
    for name in ("inspect", "record", "checkpoint", "recover"):
        result = _load_tool(name).execute({})
        assert result["status"] == "error"
        assert "project_root" in result["message"]


def test_all_compact_tools_reject_plugin_root():
    calls = {
        "inspect": {},
        "record": {"kind": "note", "summary": "invalid root"},
        "checkpoint": {"summary": "invalid root", "status": "diagnostic"},
        "recover": {},
    }
    for name, params in calls.items():
        result = _load_tool(name).execute({"project_root": str(ROOT), **params})
        assert result["status"] == "error"
        assert "plugin root" in result["message"]


def test_removed_adapters_are_not_present():
    assert sorted(path.name for path in TOOLS_DIR.glob("*.py")) == [
        "checkpoint.py",
        "inspect.py",
        "record.py",
        "recover.py",
    ]
