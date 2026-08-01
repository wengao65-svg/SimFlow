#!/usr/bin/env python3
"""Tests for HPC connector alignment and structured SSH targets.

Covers connector polymorphism, target construction, and credential boundaries.
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
    env_backup = {}
    for key in ("SIMFLOW_SLURM_HOST", "SIMFLOW_SSH_HOST", "SIMFLOW_SSH_USER", "SIMFLOW_SSH_KEY"):
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


def test_auto_detection_ignores_removed_ssh_environment():
    """Removed SSH environment variables cannot silently select a remote target."""
    env_backup = {}
    for key in ("SIMFLOW_SLURM_HOST", "SIMFLOW_SSH_HOST", "SIMFLOW_SSH_USER", "SIMFLOW_SSH_KEY"):
        env_backup[key] = os.environ.pop(key, None)

    os.environ["SIMFLOW_SSH_HOST"] = "192.168.5.6"
    os.environ["SIMFLOW_SSH_USER"] = "abinitio"
    os.environ["SIMFLOW_SSH_KEY"] = "/home/user/.ssh/hpc_key"

    try:
        from server import _get_connector
        connector = _get_connector("auto")
        from connectors.local import LocalConnector
        assert isinstance(connector, LocalConnector)
    finally:
        os.environ.pop("SIMFLOW_SSH_HOST", None)
        os.environ.pop("SIMFLOW_SSH_USER", None)
        os.environ.pop("SIMFLOW_SSH_KEY", None)
        for key, val in env_backup.items():
            if val is not None:
                os.environ[key] = val


def test_auto_detection_slurm_takes_precedence_over_ssh():
    """SLURM environment selection remains supported."""
    env_backup = {}
    for key in ("SIMFLOW_SLURM_HOST", "SIMFLOW_SSH_HOST"):
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
    """Explicit SSH requires a per-call structured target."""
    from server import _get_connector
    assert _get_connector("ssh") is None
    connector = _get_connector("ssh", {"host": "hpc"})
    from connectors.ssh import SSHConnector
    assert isinstance(connector, SSHConnector)
    assert connector.target == {"host": "hpc"}


def test_unknown_scheduler_is_rejected():
    """Unknown scheduler strings do not silently execute locally."""
    from server import _get_connector
    connector = _get_connector("nonexistent_scheduler")
    assert connector is None


def test_ssh_job_id_rejects_shell_metacharacters():
    from connectors.ssh import SSHConnector

    connector = SSHConnector(host="example.com", user="test")
    result = connector.status("123; touch /tmp/bad")
    assert result["status"] == "error"
    assert result["code"] == "invalid_job_id"


def test_ssh_connector_commands_include_user_and_port():
    from connectors.ssh import SSHConnector

    connector = SSHConnector(host="example.com", user="simflow", port=2222)
    assert connector._ssh_cmd("true") == [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        "-p", "2222", "simflow@example.com", "true",
    ]
    assert connector._scp_cmd("src", "dst") == [
        "scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        "-P", "2222", "src", "dst",
    ]


def test_ssh_alias_uses_openssh_configuration_without_overrides():
    from connectors.ssh import SSHConnector

    connector = SSHConnector(host="hpc")
    assert connector.target == {"host": "hpc"}
    assert connector._ssh_cmd("true") == [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "hpc", "true",
    ]
    assert connector._scp_cmd("src", "hpc:/scratch/job") == [
        "scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "src", "hpc:/scratch/job",
    ]


def test_ssh_direct_ip_without_port_does_not_force_port_22():
    from connectors.ssh import SSHConnector

    connector = SSHConnector(host="192.168.5.69", user="zxy")
    assert connector.target == {"host": "192.168.5.69", "user": "zxy"}
    assert connector._ssh_cmd("true")[-2:] == ["zxy@192.168.5.69", "true"]
    assert "-p" not in connector._ssh_cmd("true")


def test_ssh_diagnostics_redact_credential_paths():
    from connectors.ssh import SSHConnector

    message = SSHConnector._safe_error(
        "Load key /home/researcher/.ssh/private_hpc: bad permissions IdentityFile ~/.ssh/other",
        "failed",
    )
    assert "/home/researcher/.ssh" not in message
    assert "~/.ssh/other" not in message
    assert "<ssh-credential-path>" in message


def test_ssh_connector_brackets_ipv6_targets():
    from connectors.ssh import SSHConnector

    connector = SSHConnector(host="2001:db8::1", user="simflow")
    assert connector._remote_target() == "simflow@[2001:db8::1]"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
