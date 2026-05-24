"""HPC dry-run, script generation, and status parsing."""

import re
from typing import Optional


def generate_slurm_script(
    job_name: str,
    executable: str,
    nodes: int = 1,
    ntasks: int = 1,
    time: str = "01:00:00",
    partition: str = "normal",
    account: Optional[str] = None,
    mem: Optional[str] = None,
    output: str = "job.out",
    error: str = "job.err",
    modules: Optional[list] = None,
    pre_commands: Optional[list] = None,
    mpi_launcher: str = "mpirun",
) -> str:
    """Generate a SLURM job script."""
    lines = [
        "#!/bin/bash",
        f"#SBATCH --job-name={job_name}",
        f"#SBATCH --nodes={nodes}",
        f"#SBATCH --ntasks={ntasks}",
        f"#SBATCH --time={time}",
        f"#SBATCH --partition={partition}",
        f"#SBATCH --output={output}",
        f"#SBATCH --error={error}",
    ]
    if account:
        lines.append(f"#SBATCH --account={account}")
    if mem:
        lines.append(f"#SBATCH --mem={mem}")

    lines.append("")
    if modules:
        for mod in modules:
            lines.append(f"module load {mod}")
        lines.append("")

    if pre_commands:
        for cmd in pre_commands:
            lines.append(cmd)
        lines.append("")

    lines.append(f"{mpi_launcher} {executable}")
    return "\n".join(lines) + "\n"


def generate_pbs_script(
    job_name: str,
    executable: str,
    nodes: int = 1,
    ppn: int = 1,
    walltime: str = "01:00:00",
    queue: str = "default",
    account: Optional[str] = None,
    mem: Optional[str] = None,
    output: str = "job.out",
    error: str = "job.err",
    modules: Optional[list] = None,
    pre_commands: Optional[list] = None,
    mpi_launcher: str = "mpirun",
) -> str:
    """Generate a PBS job script."""
    lines = [
        "#!/bin/bash",
        f"#PBS -N {job_name}",
        f"#PBS -l nodes={nodes}:ppn={ppn}",
        f"#PBS -l walltime={walltime}",
        f"#PBS -q {queue}",
        f"#PBS -o {output}",
        f"#PBS -e {error}",
    ]
    if account:
        lines.append(f"#PBS -A {account}")
    if mem:
        lines.append(f"#PBS -l mem={mem}")

    lines.append("")
    lines.append("cd $PBS_O_WORKDIR")
    lines.append("")

    if modules:
        for mod in modules:
            lines.append(f"module load {mod}")
        lines.append("")

    if pre_commands:
        for cmd in pre_commands:
            lines.append(cmd)
        lines.append("")

    lines.append(f"{mpi_launcher} {executable}")
    return "\n".join(lines) + "\n"


def parse_slurm_status(output: str) -> dict:
    """Parse squeue output to extract job status."""
    jobs = []
    for line in output.strip().split("\n")[1:]:  # skip header
        parts = line.split()
        if len(parts) >= 5:
            jobs.append({
                "job_id": parts[0],
                "name": parts[1],
                "user": parts[2],
                "status": parts[4],
                "time": parts[5] if len(parts) > 5 else None,
            })
    return {"jobs": jobs}


def parse_slurm_job_id(output: str) -> Optional[str]:
    """Extract job ID from sbatch output."""
    match = re.search(r"Submitted batch job (\d+)", output)
    return match.group(1) if match else None


def estimate_resources(
    software: str,
    job_type: str,
    num_atoms: int,
    num_kpoints: int = 1,
) -> dict:
    """Estimate resource requirements for a calculation."""
    # Basic heuristic estimates
    base_walltime_hours = {
        "vasp": {"scf": 1, "relax": 4, "md": 8, "bands": 2},
        "qe": {"scf": 1, "relax": 3, "md": 6, "bands": 2},
        "lammps": {"equilibrate": 2, "production": 8, "minimize": 1},
        "gaussian": {"optimize": 2, "frequency": 4, "sp": 1},
    }

    sw = base_walltime_hours.get(software, {})
    base_hours = sw.get(job_type, 2)

    # Scale by atom count (rough heuristic)
    scale = max(1, num_atoms / 50)
    est_hours = base_hours * scale

    # Scale by k-points
    k_scale = max(1, num_kpoints / 4)
    est_hours *= k_scale

    nodes = max(1, int(est_hours / 4))
    ntasks = min(nodes * 16, 128)

    return {
        "estimated_walltime_hours": round(est_hours, 1),
        "recommended_nodes": nodes,
        "recommended_ntasks": ntasks,
        "recommended_memory_gb": max(16, num_atoms * 2),
    }
