"""Generate scheduler scripts and rough resource estimates without submitting."""

from __future__ import annotations

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
        lines.extend(f"module load {mod}" for mod in modules)
        lines.append("")
    if pre_commands:
        lines.extend(pre_commands)
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
    lines.extend(["", "cd $PBS_O_WORKDIR", ""])
    if modules:
        lines.extend(f"module load {mod}" for mod in modules)
        lines.append("")
    if pre_commands:
        lines.extend(pre_commands)
        lines.append("")
    lines.append(f"{mpi_launcher} {executable}")
    return "\n".join(lines) + "\n"


def estimate_resources(software: str, job_type: str, num_atoms: int, num_kpoints: int = 1) -> dict:
    """Return a heuristic estimate for user review; it does not authorize execution."""
    base_walltime_hours = {
        "vasp": {"scf": 1, "relax": 4, "md": 8, "bands": 2},
        "qe": {"scf": 1, "relax": 3, "md": 6, "bands": 2},
        "lammps": {"equilibrate": 2, "production": 8, "minimize": 1},
        "gaussian": {"optimize": 2, "frequency": 4, "sp": 1},
    }
    base_hours = base_walltime_hours.get(software, {}).get(job_type, 2)
    est_hours = base_hours * max(1, num_atoms / 50) * max(1, num_kpoints / 4)
    nodes = max(1, int(est_hours / 4))
    return {
        "estimated_walltime_hours": round(est_hours, 1),
        "recommended_nodes": nodes,
        "recommended_ntasks": min(nodes * 16, 128),
        "recommended_memory_gb": max(16, num_atoms * 2),
    }
