#!/usr/bin/env python3
"""Prepare HPC job submission scripts.

Generates SLURM or PBS scripts from job configuration, with optional
dry-run mode to validate without submission.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "runtime" / "lib"))

from hpc import generate_slurm_script, generate_pbs_script, estimate_resources


def prepare_slurm_job(config: dict) -> dict:
    """Generate SLURM job script."""
    script = generate_slurm_script(
        job_name=config.get("job_name", "simflow"),
        executable=config.get("executable", "vasp_std"),
        nodes=config.get("nodes", 1),
        ntasks=config.get("ntasks", 16),
        time=config.get("time", "01:00:00"),
        partition=config.get("partition", "normal"),
        account=config.get("account"),
        mem=config.get("mem"),
        output=config.get("output", "job.out"),
        error=config.get("error", "job.err"),
        modules=config.get("modules"),
        pre_commands=config.get("pre_commands"),
        mpi_launcher=config.get("mpi_launcher", "mpirun"),
    )

    return {"scheduler": "slurm", "script": script}


def prepare_pbs_job(config: dict) -> dict:
    """Generate PBS job script."""
    script = generate_pbs_script(
        job_name=config.get("job_name", "simflow"),
        executable=config.get("executable", "vasp_std"),
        nodes=config.get("nodes", 1),
        ppn=config.get("ppn", 16),
        walltime=config.get("walltime", "01:00:00"),
        queue=config.get("queue", "default"),
        account=config.get("account"),
        mem=config.get("mem"),
        output=config.get("output", "job.out"),
        error=config.get("error", "job.err"),
        modules=config.get("modules"),
        pre_commands=config.get("pre_commands"),
        mpi_launcher=config.get("mpi_launcher", "mpirun"),
    )

    return {"scheduler": "pbs", "script": script}


def prepare_job(config: dict, scheduler: str, output_dir: str, dry_run: bool = True) -> dict:
    """Prepare job submission script."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Estimate resources if not specified
    if "nodes" not in config and "software" in config:
        est = estimate_resources(
            config["software"],
            config.get("job_type", "scf"),
            config.get("num_atoms", 50),
            config.get("num_kpoints", 1),
        )
        config.setdefault("nodes", est["recommended_nodes"])
        config.setdefault("ntasks", est["recommended_ntasks"])
        mem_gb = est["recommended_memory_gb"]
        config.setdefault("mem", "{}GB".format(mem_gb))
        resource_estimate = est
    else:
        resource_estimate = None

    if scheduler == "slurm":
        result = prepare_slurm_job(config)
        script_name = "submit.sh"
    elif scheduler == "pbs":
        result = prepare_pbs_job(config)
        script_name = "submit.pbs"
    else:
        raise ValueError("Unsupported scheduler: {}".format(scheduler))

    script_path = output_path / script_name
    script_path.write_text(result["script"])

    return {
        "status": "success",
        "scheduler": scheduler,
        "script_path": str(script_path),
        "dry_run": dry_run,
        "config": {k: v for k, v in config.items() if k != "pre_commands"},
        "resource_estimate": resource_estimate,
        "executable": config.get("executable"),
    }


def main():
    parser = argparse.ArgumentParser(description="Prepare HPC job scripts")
    parser.add_argument("--scheduler", required=True, choices=["slurm", "pbs"],
                        help="Job scheduler type")
    parser.add_argument("--config", required=True,
                        help="JSON file with job configuration")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Generate script without submitting")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false",
                        help="Mark as ready for submission")
    args = parser.parse_args()

    try:
        with open(args.config) as f:
            config = json.load(f)
        result = prepare_job(config, args.scheduler, args.output_dir, args.dry_run)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
