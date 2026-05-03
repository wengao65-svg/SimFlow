"""Local environment detection: Python, SSH, tmux, compute software, MPI."""

import os
import shutil
import subprocess
from typing import Optional


def detect_python() -> dict:
    """Detect Python environment."""
    import sys
    return {
        "available": True,
        "version": sys.version,
        "executable": sys.executable,
        "platform": sys.platform,
    }


def detect_ssh() -> dict:
    """Detect SSH availability."""
    ssh_bin = shutil.which("ssh")
    ssh_key = os.path.expanduser("~/.ssh/id_rsa")
    return {
        "available": ssh_bin is not None,
        "path": ssh_bin,
        "has_key": os.path.exists(ssh_key),
    }


def detect_tmux() -> dict:
    """Detect tmux availability."""
    tmux_bin = shutil.which("tmux")
    has_session = False
    if tmux_bin:
        try:
            result = subprocess.run(
                ["tmux", "list-sessions"],
                capture_output=True, timeout=5,
            )
            has_session = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return {
        "available": tmux_bin is not None,
        "path": tmux_bin,
        "has_session": has_session,
    }


def detect_mpi() -> dict:
    """Detect MPI installation."""
    mpirun = shutil.which("mpirun")
    mpiexec = shutil.which("mpiexec")
    srun = shutil.which("srun")
    launcher = srun or mpirun or mpiexec
    return {
        "available": launcher is not None,
        "mpirun": mpirun,
        "mpiexec": mpiexec,
        "srun": srun,
        "launcher": launcher,
    }


def detect_software() -> dict:
    """Detect computational chemistry software."""
    software = {}

    # VASP
    vasp_std = shutil.which("vasp_std")
    vasp_gam = shutil.which("vasp_gam")
    vasp_ncl = shutil.which("vasp_ncl")
    software["vasp"] = {
        "available": any([vasp_std, vasp_gam, vasp_ncl]),
        "vasp_std": vasp_std,
        "vasp_gam": vasp_gam,
        "vasp_ncl": vasp_ncl,
    }

    # Quantum ESPRESSO
    pw_x = shutil.which("pw.x")
    software["qe"] = {
        "available": pw_x is not None,
        "pw_x": pw_x,
    }

    # LAMMPS
    lammps = shutil.which("lmp") or shutil.which("lmp_serial") or shutil.which("lammps")
    software["lammps"] = {
        "available": lammps is not None,
        "executable": lammps,
    }

    # Gaussian
    g16 = shutil.which("g16") or shutil.which("g09")
    software["gaussian"] = {
        "available": g16 is not None,
        "executable": g16,
    }

    return software


def detect_slurm() -> dict:
    """Detect SLURM availability."""
    sbatch = shutil.which("sbatch")
    scancel = shutil.which("scancel")
    squeue = shutil.which("squeue")
    return {
        "available": sbatch is not None,
        "sbatch": sbatch,
        "scancel": scancel,
        "squeue": squeue,
    }


def detect_pbs() -> dict:
    """Detect PBS availability."""
    qsub = shutil.which("qsub")
    qdel = shutil.which("qdel")
    qstat = shutil.which("qstat")
    return {
        "available": qsub is not None,
        "qsub": qsub,
        "qdel": qdel,
        "qstat": qstat,
    }


def detect_environment() -> dict:
    """Run full environment detection."""
    return {
        "python": detect_python(),
        "ssh": detect_ssh(),
        "tmux": detect_tmux(),
        "mpi": detect_mpi(),
        "software": detect_software(),
        "scheduler": {
            "slurm": detect_slurm(),
            "pbs": detect_pbs(),
        },
    }
