#!/usr/bin/env python3
"""Tests for HPC connector signature alignment and SSH workstation auto-detection.

Covers P0.2:
- LocalConnector.dry_run() signature mismatch (took 2 positional args, got 4)
- Auto-detection defaults to SlurmConnector, ignoring SSH workstation mode
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]  # tests/mcp/ -> simflow/
HPC_DIR = ROOT / "mcp" / "servers" / "hpc"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(HPC_DIR))


@pytest.fixture(autouse=True)
def _isolate_hpc_modules():
    """Purge cached 'connectors' and 'server' modules, re-prioritize hpc path."""
    to_remove = [
        k for k in list(sys.modules)
        if k == "connectors" or k.startswith("connectors.") or k == "server"
    ]
    for k in to_remove:
        del sys.modules[k]
    hpc_dir_str = str(HPC_DIR)
    if hpc_dir_str in sys.path:
        sys.path.remove(hpc_dir_str)
    sys.path.insert(0, hpc_dir_str)
    yield
    to_remove = [
        k for k in list(sys.modules)
        if k == "connectors" or k.startswith("connectors.") or k == "server"
    ]
    for k in to_remove:
        del sys.modules[k]


def test_local_connector_dry_run_accepts_three_args():
    """LocalConnector.dry_run must accept (script_path, manifest_path, base_dir)."""
    from connectors.local import LocalConnector

    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "test.sh"
        script.write_text("#!/bin/bash\necho hello\n", encoding="utf-8")
        script.chmod(0o755)

        connector = LocalConnector()
        # Must not raise "takes 2 positional arguments but 4 were given"
        result = connector.dry_run(str(script), manifest_path="", base_dir=tmpdir)
        assert result["valid"] is True
        assert result["scheduler"] == "local"
        assert "script_hash" in result


def test_pbs_connector_dry_run_accepts_three_args():
    """PBSConnector.dry_run must accept (script_path, manifest_path, base_dir)."""
    from connectors.pbs import PBSConnector

    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "test.pbs"
        script.write_text("#!/bin/bash\n#PBS -N test\necho hello\n", encoding="utf-8")
        script.chmod(0o755)

        connector = PBSConnector()
        result = connector.dry_run(str(script), manifest_path="", base_dir=tmpdir)
        assert result["scheduler"] == "pbs"


def test_ssh_connector_dry_run_accepts_three_args():
    """SSHConnector.dry_run must accept (script_path, manifest_path, base_dir)."""
    from connectors.ssh import SSHConnector

    with tempfile.TemporaryDirectory() as tmpdir:
        script = Path(tmpdir) / "test.sh"
        script.write_text("#!/bin/bash\necho hello\n", encoding="utf-8")
        script.chmod(0o755)

        connector = SSHConnector(host="example.com", user="test")
        result = connector.dry_run(str(script), manifest_path="", base_dir=tmpdir)
        assert result["scheduler"] == "ssh"


def test_auto_detection_defaults_to_local_without_env():
    """Auto-detection returns LocalConnector when no SSH/SLURM env is set."""
    # Clear relevant env vars
    env_backup = {}
    for key in ("SIMFLOW_SLURM_HOST", "SIMFLOW_SSH_HOST", "SIMFLOW_SSH_USER", "SIMFLOW_SSH_KEY", "SIMFLOW_SSH_WORKSTATION_MODE"):
        env_backup[key] = os.environ.pop(key, None)

    try:
        from server import _get_connector
        connector = _get_connector("auto")
        from connectors.local import LocalConnector
        assert isinstance(connector, LocalConnector), f"expected LocalConnector, got {type(connector)}"
    finally:
        for key, val in env_backup.items():
            if val is not None:
                os.environ[key] = val


def test_auto_detection_returns_ssh_when_ssh_host_set():
    """Auto-detection returns SSHConnector when SIMFLOW_SSH_HOST is set."""
    env_backup = {}
    for key in ("SIMFLOW_SLURM_HOST", "SIMFLOW_SSH_HOST", "SIMFLOW_SSH_WORKSTATION_MODE"):
        env_backup[key] = os.environ.pop(key, None)

    os.environ["SIMFLOW_SSH_HOST"] = "192.168.5.6"
    os.environ["SIMFLOW_SSH_USER"] = "abinitio"

    try:
        from server import _get_connector
        connector = _get_connector("auto")
        from connectors.ssh import SSHConnector
        assert isinstance(connector, SSHConnector), f"expected SSHConnector, got {type(connector)}"
        assert connector.host == "192.168.5.6"
        assert connector.user == "abinitio"
    finally:
        os.environ.pop("SIMFLOW_SSH_HOST", None)
        os.environ.pop("SIMFLOW_SSH_USER", None)
        for key, val in env_backup.items():
            if val is not None:
                os.environ[key] = val


def test_auto_detection_returns_ssh_when_workstation_mode_set():
    """Auto-detection returns SSHConnector when SIMFLOW_SSH_WORKSTATION_MODE=1."""
    env_backup = {}
    for key in ("SIMFLOW_SLURM_HOST", "SIMFLOW_SSH_HOST", "SIMFLOW_SSH_WORKSTATION_MODE"):
        env_backup[key] = os.environ.pop(key, None)

    os.environ["SIMFLOW_SSH_WORKSTATION_MODE"] = "1"
    os.environ["SIMFLOW_SSH_HOST"] = "workstation.example.com"

    try:
        from server import _get_connector
        connector = _get_connector("auto")
        from connectors.ssh import SSHConnector
        assert isinstance(connector, SSHConnector)
    finally:
        os.environ.pop("SIMFLOW_SSH_WORKSTATION_MODE", None)
        os.environ.pop("SIMFLOW_SSH_HOST", None)
        for key, val in env_backup.items():
            if val is not None:
                os.environ[key] = val


def test_auto_detection_slurm_takes_precedence_over_ssh():
    """When both SLURM and SSH env vars are set, SLURM takes precedence."""
    env_backup = {}
    for key in ("SIMFLOW_SLURM_HOST", "SIMFLOW_SSH_HOST", "SIMFLOW_SSH_WORKSTATION_MODE"):
        env_backup[key] = os.environ.pop(key, None)

    os.environ["SIMFLOW_SLURM_HOST"] = "hpc.cluster.example.com"
    os.environ["SIMFLOW_SSH_HOST"] = "192.168.5.6"

    try:
        from server import _get_connector
        connector = _get_connector("auto")
        from connectors.slurm import SlurmConnector
        assert isinstance(connector, SlurmConnector), f"expected SlurmConnector, got {type(connector)}"
    finally:
        os.environ.pop("SIMFLOW_SLURM_HOST", None)
        os.environ.pop("SIMFLOW_SSH_HOST", None)
        for key, val in env_backup.items():
            if val is not None:
                os.environ[key] = val


def test_explicit_scheduler_local():
    """Explicit scheduler='local' returns LocalConnector."""
    from server import _get_connector
    connector = _get_connector("local")
    from connectors.local import LocalConnector
    assert isinstance(connector, LocalConnector)


def test_explicit_scheduler_ssh():
    """Explicit scheduler='ssh' returns SSHConnector when env configured."""
    env_backup = os.environ.pop("SIMFLOW_SSH_HOST", None)
    os.environ["SIMFLOW_SSH_HOST"] = "test.example.com"
    try:
        from server import _get_connector
        connector = _get_connector("ssh")
        from connectors.ssh import SSHConnector
        assert isinstance(connector, SSHConnector)
    finally:
        if env_backup is not None:
            os.environ["SIMFLOW_SSH_HOST"] = env_backup
        else:
            os.environ.pop("SIMFLOW_SSH_HOST", None)


def test_unknown_scheduler_falls_back_to_local():
    """Unknown scheduler string falls back to LocalConnector."""
    from server import _get_connector
    connector = _get_connector("nonexistent_scheduler")
    from connectors.local import LocalConnector
    assert isinstance(connector, LocalConnector)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
