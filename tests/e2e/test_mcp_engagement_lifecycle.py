"""End-to-end coverage for the compact state record lifecycle."""

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_state_server():
    server_dir = ROOT / "mcp" / "servers" / "simflow_state"
    for name in [name for name in sys.modules if name == "tools" or name.startswith("tools.")]:
        del sys.modules[name]
    sys.path.insert(0, str(server_dir))
    spec = importlib.util.spec_from_file_location("compact_state_lifecycle", server_dir / "server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mcp_record_checkpoint_recover_lifecycle(tmp_path):
    output = tmp_path / "outputs" / "result.dat"
    output.parent.mkdir()
    output.write_text("1 2 3\n", encoding="utf-8")
    server = _load_state_server()

    initial = server.handle_request({"tool": "inspect", "params": {"project_root": str(tmp_path)}})
    assert initial["status"] == "success"
    assert initial["data"]["initialized"] is False

    run = server.handle_request({
        "tool": "record",
        "params": {
            "project_root": str(tmp_path),
            "kind": "run",
            "summary": "Computation paused after validated output",
            "status": "paused",
            "stage": "computation",
            "artifacts": [{"path": "outputs/result.dat", "role": "logical_run_output"}],
            "next_action": "resume from validated output",
        },
    })
    assert run["status"] == "success"

    checkpoint = server.handle_request({
        "tool": "checkpoint",
        "params": {
            "project_root": str(tmp_path),
            "summary": "Resume computation",
            "run_id": run["data"]["run_id"],
            "restart_refs": ["outputs/result.dat"],
            "resume_command": "solver --restart outputs/result.dat",
        },
    })
    assert checkpoint["status"] == "success"
    assert "state_snapshot" not in checkpoint["data"]

    recovered = server.handle_request({"tool": "recover", "params": {"project_root": str(tmp_path)}})
    assert recovered["status"] == "success"
    assert recovered["data"]["ready"] is True
    assert recovered["data"]["checkpoint"]["checkpoint_id"] == checkpoint["data"]["checkpoint_id"]

    final = server.handle_request({"tool": "inspect", "params": {"project_root": str(tmp_path)}})
    assert final["data"]["project"]["counts"]["by_kind"] == {"checkpoint": 1, "run": 1}
    assert final["data"]["project"]["current"]["active_run_id"] == run["data"]["run_id"]
    assert not (tmp_path / ".simflow" / "state").exists()
