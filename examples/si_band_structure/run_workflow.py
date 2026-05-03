#!/usr/bin/env python3
"""Si band structure DFT workflow: relax → scf → bands.

Uses SimFlow for state tracking and SSH HPC connector for job submission.
Runs on HPC: cancon.hpccube.com via SLURM with VASP 6.4.2-dtk24.04.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add runtime to path
SCRIPT_DIR = Path(__file__).parent
SIMFLOW_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SIMFLOW_ROOT / "runtime"))

from lib.state import init_workflow, update_stage, read_state
from lib.template import render_string

# === Configuration ===
HPC_HOST = "hpc"
HPC_USER = "ac4iry5343"
HPC_BASE = f"/public/home/{HPC_USER}/simflow/si_band"
VASP_ENV = "/public/home/ac4iry5343/apprepo/vasp/6.4.2-dtk24.04_all_nohdf5/scripts/env.sh"

STEPS = ["relax", "scf", "bands"]
SLURM_TEMPLATE = """#!/bin/bash
#SBATCH -N 1
#SBATCH --ntasks-per-node=4
#SBATCH -c 8
#SBATCH -J Si-{{ step }}
#SBATCH --gres=dcu:4
#SBATCH -p kshdtest
#SBATCH -t {{ walltime }}

module purge
source {{ vasp_env }}

VASP_EXE=vasp_std

config=config.${SLURM_JOB_ID}
echo -e "-genv OMP_NUM_THREADS 6 \\c" > $config
for i in $(scontrol show hostnames $SLURM_NODELIST)
do
  for ((j=0; j<4; j++))
  do
    echo "-host $i -env HIP_VISIBLE_DEVICES $j -n 1 numactl --cpunodebind=$j --membind=$j $VASP_EXE" >> $config
  done
done

ulimit -s unlimited
export NCCL_IB_HCA="mlx5_0"
export HSA_FORCE_FINE_GRAIN_PCIE=1

mpirun -configfile $config
"""


def ssh_cmd(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Execute command on HPC via SSH."""
    full_cmd = ["ssh", "-o", "ConnectTimeout=10", HPC_HOST, cmd]
    result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=300)
    if check and result.returncode != 0:
        print(f"  SSH error: {result.stderr}")
        if result.returncode != 0:
            raise RuntimeError(f"SSH command failed: {cmd}")
    return result


def scp_to_hpc(local_path: str, remote_path: str):
    """Copy file to HPC."""
    subprocess.run(
        ["scp", "-o", "ConnectTimeout=10", local_path, f"{HPC_HOST}:{remote_path}"],
        capture_output=True, check=True, timeout=60,
    )


def scp_from_hpc(remote_path: str, local_path: str):
    """Copy file from HPC."""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    subprocess.run(
        ["scp", "-o", "ConnectTimeout=10", f"{HPC_HOST}:{remote_path}", local_path],
        capture_output=True, check=True, timeout=120,
    )


def setup_hpc_directory(step: str):
    """Create step directory on HPC and upload input files."""
    remote_dir = f"{HPC_BASE}/{step}"
    ssh_cmd(f"mkdir -p {remote_dir}")

    local_dir = SCRIPT_DIR / step
    files_to_upload = ["INCAR", "KPOINTS", "POSCAR", "POTCAR"]
    if step == "bands":
        files_to_upload.extend(["WAVECAR", "CHGCAR"])
    for fname in files_to_upload:
        local_file = local_dir / fname
        if local_file.exists():
            scp_to_hpc(str(local_file), f"{remote_dir}/{fname}")

    # Generate and upload SLURM script
    slurm_content = render_string(SLURM_TEMPLATE, {
        "step": step,
        "walltime": "00:30:00",
        "vasp_env": VASP_ENV,
    })
    slurm_path = str(local_dir / "vasp.slurm")
    with open(slurm_path, "w") as f:
        f.write(slurm_content)
    scp_to_hpc(slurm_path, f"{remote_dir}/vasp.slurm")

    return remote_dir


def submit_slurm_job(remote_dir: str) -> str:
    """Submit SLURM job and return job ID."""
    result = ssh_cmd(f"cd {remote_dir} && sbatch vasp.slurm 2>&1")
    output = result.stdout.strip()
    # Parse "Submitted batch job 12345"
    if "Submitted batch job" in output:
        job_id = output.split()[-1]
        return job_id
    raise RuntimeError(f"Failed to parse sbatch output: {output}")


def check_slurm_job(job_id: str) -> str:
    """Check SLURM job status. Returns: RUNNING, COMPLETED, FAILED, or UNKNOWN."""
    result = ssh_cmd(f"sacct -j {job_id} --format=State --noheader 2>/dev/null", check=False)
    if result.stdout:
        state = result.stdout.strip().split()[0].strip()
        if "RUNNING" in state or "PENDING" in state:
            return "RUNNING"
        elif "COMPLETED" in state:
            return "COMPLETED"
        elif "FAILED" in state or "CANCELLED" in state or "TIMEOUT" in state:
            return "FAILED"
    return "UNKNOWN"


def wait_for_job(job_id: str, poll_interval: int = 30) -> str:
    """Wait for SLURM job to complete."""
    print(f"  Waiting for job {job_id}...")
    while True:
        status = check_slurm_job(job_id)
        if status == "COMPLETED":
            print(f"  Job {job_id} completed")
            return "COMPLETED"
        elif status == "FAILED":
            print(f"  Job {job_id} failed")
            return "FAILED"
        elif status == "RUNNING":
            print(f"  Job {job_id} running...", end="\r")
            time.sleep(poll_interval)
        else:
            # Job might have finished and left sacct
            time.sleep(poll_interval)
            # Check if output files exist
            result = ssh_cmd(f"ls {HPC_BASE}/*/OUTCAR 2>/dev/null", check=False)
            if result.stdout:
                return "COMPLETED"


def download_results(step: str):
    """Download results from HPC."""
    remote_dir = f"{HPC_BASE}/{step}"
    local_dir = SCRIPT_DIR / step / "output"
    os.makedirs(local_dir, exist_ok=True)

    for fname in ["OUTCAR", "OSZICAR", "CONTCAR", "vasprun.xml"]:
        try:
            scp_from_hpc(f"{remote_dir}/{fname}", str(local_dir / fname))
        except Exception:
            pass


def parse_relaxation_energy(step_dir: str) -> float:
    """Parse final energy from OSZICAR."""
    oszicar = Path(step_dir) / "output" / "OSZICAR"
    if not oszicar.exists():
        return None
    energy = None
    for line in open(oszicar):
        if "E0=" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "E0=":
                    energy = float(parts[i + 1])
    return energy


def check_convergence(step_dir: str) -> bool:
    """Check if VASP calculation converged."""
    outcar = Path(step_dir) / "output" / "OUTCAR"
    if not outcar.exists():
        return False
    content = outcar.read_text()
    return "reached required accuracy" in content or "aborting loop" not in content


def main():
    print("=" * 60)
    print("Si Band Structure DFT Workflow")
    print("Relaxation → SCF → Band Structure")
    print("=" * 60)

    # Initialize SimFlow state
    result = init_workflow("dft", entry_point="input_generation")
    wf_id = result["workflow_id"]
    print(f"\nWorkflow ID: {wf_id}")
    print(f"State dir: {SIMFLOW_ROOT / '.simflow'}")

    # Run each step, with inter-step file passing
    for step_idx, step in enumerate(STEPS):
        print(f"\n{'='*40}")
        print(f"Step: {step.upper()}")
        print(f"{'='*40}")

        # Update SimFlow stage
        update_stage(f"compute_{step}", "in_progress")

        # Setup HPC directory
        print(f"  Setting up HPC directory for {step}...")
        remote_dir = setup_hpc_directory(step)

        # Submit SLURM job
        print(f"  Submitting SLURM job...")
        job_id = submit_slurm_job(remote_dir)
        print(f"  Job ID: {job_id}")

        # Update SimFlow with job ID
        update_stage(f"compute_{step}", "in_progress", job_id=job_id)

        # Wait for completion
        status = wait_for_job(job_id)

        if status == "COMPLETED":
            # Download results
            print(f"  Downloading results...")
            download_results(step)

            # Check convergence
            converged = check_convergence(SCRIPT_DIR / step)
            energy = parse_relaxation_energy(SCRIPT_DIR / step)

            if converged:
                print(f"  Converged! Energy: {energy} eV")
                update_stage(f"compute_{step}", "completed", energy=energy)

                # Pass relaxed structure to next steps
                if step == "relax":
                    contcar = SCRIPT_DIR / "relax" / "output" / "CONTCAR"
                    if contcar.exists():
                        for next_step in ["scf", "bands"]:
                            dest = SCRIPT_DIR / next_step / "POSCAR"
                            import shutil
                            shutil.copy2(str(contcar), str(dest))
                            print(f"  Copied relaxed structure to {next_step}/POSCAR")

                # Pass charge density to bands step
                if step == "scf":
                    for fname in ["WAVECAR", "CHGCAR"]:
                        src = SCRIPT_DIR / "scf" / "output" / fname
                        if src.exists():
                            dest = SCRIPT_DIR / "bands" / fname
                            import shutil
                            shutil.copy2(str(src), str(dest))
                            print(f"  Copied {fname} to bands/")
            else:
                print(f"  WARNING: Calculation did not converge")
                update_stage(f"compute_{step}", "failed", reason="not_converged")
                sys.exit(1)
        else:
            print(f"  ERROR: Job {job_id} failed")
            update_stage(f"compute_{step}", "failed", reason="job_failed")
            sys.exit(1)

    # Final summary
    print(f"\n{'='*60}")
    print("Workflow Complete!")
    print(f"{'='*60}")

    relax_energy = parse_relaxation_energy(SCRIPT_DIR / "relax")
    scf_energy = parse_relaxation_energy(SCRIPT_DIR / "scf")

    print(f"\nResults:")
    print(f"  Relax energy: {relax_energy} eV")
    print(f"  SCF energy:   {scf_energy} eV")
    print(f"  Bands:        {SCRIPT_DIR / 'bands' / 'output'}")
    print(f"\nState dir: {SIMFLOW_ROOT / '.simflow'}")

    # Print final state
    state = read_state(str(SIMFLOW_ROOT))
    print(f"\nFinal workflow state:")
    print(json.dumps(state, indent=2, default=str))


if __name__ == "__main__":
    main()
