"""HPC MCP Server.

Provides HPC job management tools.
Supports multiple schedulers: slurm, pbs, local, ssh.
Default mode: dry-run only. Real submission requires approval gate.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from connectors.slurm import SlurmConnector
from connectors.pbs import PBSConnector
from connectors.local import LocalConnector
from connectors.ssh import SSHConnector
from mcp.shared.transport import dispatch_request, run_server


_CONNECTORS = {
    "slurm": SlurmConnector,
    "pbs": PBSConnector,
    "local": LocalConnector,
    "ssh": SSHConnector,
}

_default = SlurmConnector()


def _get_connector(scheduler: str = "auto"):
    """Get a connector instance, with auto-detection and fallback."""
    if scheduler == "auto":
        return _default
    cls = _CONNECTORS.get(scheduler)
    if cls is None:
        return None
    try:
        return cls()
    except Exception:
        return _default


def handle_dry_run(params: dict) -> dict:
    """Validate a job script without submitting."""
    script_path = params.get("script_path", "")
    manifest_path = params.get("manifest_path", "")
    base_dir = params.get("base_dir", ".")
    scheduler = params.get("scheduler", "auto")
    if not script_path:
        return {"status": "error", "message": "script_path is required"}

    connector = _get_connector(scheduler)
    if connector is None:
        return {"status": "error", "message": "Unknown scheduler: {}".format(scheduler)}

    result = connector.dry_run(script_path, manifest_path, base_dir)
    return {"status": "success", "data": result}


def handle_prepare(params: dict) -> dict:
    """Prepare a job script (generate SLURM script)."""
    from runtime.lib.hpc import generate_slurm_script

    job_name = params.get("job_name", "simflow_job")
    executable = params.get("executable", "vasp_std")
    nodes = params.get("nodes", 1)
    ntasks = params.get("ntasks", 16)
    walltime = params.get("walltime", "04:00:00")

    script = generate_slurm_script(
        job_name=job_name,
        executable=executable,
        nodes=nodes,
        ntasks=ntasks,
        time=walltime,
    )
    return {"status": "success", "data": {"script": script, "job_name": job_name}}


def handle_status(params: dict) -> dict:
    """Check job status."""
    job_id = params.get("job_id", "")
    scheduler = params.get("scheduler", "auto")
    if not job_id:
        return {"status": "error", "message": "job_id is required"}

    connector = _get_connector(scheduler)
    if connector is None:
        return {"status": "error", "message": "Unknown scheduler: {}".format(scheduler)}

    result = connector.status(job_id)
    return result


def handle_submit(params: dict) -> dict:
    """Submit a job (requires scheduler parameter)."""
    script_path = params.get("script_path", "")
    scheduler = params.get("scheduler", "auto")
    if not script_path:
        return {"status": "error", "message": "script_path is required"}

    connector = _get_connector(scheduler)
    if connector is None:
        return {"status": "error", "message": "Unknown scheduler: {}".format(scheduler)}

    result = connector.submit(script_path)
    return result


TOOLS = {
    "dry_run": handle_dry_run,
    "prepare": handle_prepare,
    "status": handle_status,
    "submit": handle_submit,
}

TOOL_DESCRIPTIONS = {
    "dry_run": "Validate an HPC job script without submitting it.",
    "prepare": "Prepare a scheduler job script for review.",
    "status": "Check scheduler job status through safe connector abstractions.",
    "submit": "Submit a job only when SimFlow approval and safety gates allow it.",
}


def handle_request(request: dict) -> dict:
    """Dispatch a request to the appropriate tool handler."""
    return dispatch_request(request, TOOLS)


if __name__ == "__main__":
    from mcp.shared.stdio_server import run_mcp_server

    run_mcp_server("hpc", TOOLS, TOOL_DESCRIPTIONS)
