#!/usr/bin/env python3
"""H2O CP2K workflow: AIMD NVT (200 steps) -> extract last frame -> DFT single point.

HPC: ssh hpc, CP2K v2025.1-oneapi2024, SLURM kshctest partition.

Usage:
    python run_cp2k_workflow.py --dry-run    # Generate inputs only
    python run_cp2k_workflow.py --submit     # Submit to HPC and wait
    python run_cp2k_workflow.py --status     # Check HPC job status
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SIMFLOW_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SIMFLOW_ROOT / "runtime"))

from lib.cp2k_input import (
    extract_last_frame,
    generate_input,
    read_cif_to_xyz,
    write_xyz,
)
from lib.parsers.cp2k_parser import CP2KParser

# === HPC Configuration ===
HPC_HOST = "hpc"
REMOTE_BASE = "simflow/h2o_cp2k"
CP2K_ENV = "source /public/home/ac4iry5343/apprepo/cp2k/v2025.1-oneapi2024/scripts/env.sh"
CP2K_EXE = "/public/home/ac4iry5343/apprepo/cp2k/v2025.1-oneapi2024/app/bin/cp2k.psmp"
SLURM_PARTITION = "kshctest"
SLURM_WALLTIME = "02:00:00"
SLURM_NTASKS = 64

# === Local paths ===
CIF_FILE = SCRIPT_DIR / "H2O.cif"
AIMD_DIR = SCRIPT_DIR / "aimd"
DFT_DIR = SCRIPT_DIR / "dft_sp"

# === Workflow parameters ===
AIMD_PARAMS = {
    "project_name": "H2O_aimd_nvt",
    "steps": 200,
    "timestep": 0.5,
    "temperature": 300.0,
}

ENERGY_PARAMS = {
    "project_name": "H2O_energy",
}


# =============================================================================
# SSH/SCP helpers
# =============================================================================

def ssh_cmd(cmd: str, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    """Execute command on HPC via SSH."""
    full_cmd = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", HPC_HOST, cmd]
    result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        print(f"  SSH error (rc={result.returncode}): {result.stderr.strip()}")
        if check:
            raise RuntimeError(f"SSH command failed: {cmd}")
    return result


def scp_to_hpc(local_path: str, remote_path: str):
    """Copy file to HPC."""
    subprocess.run(
        ["scp", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
         local_path, f"{HPC_HOST}:{remote_path}"],
        capture_output=True, check=True, timeout=120,
    )


def scp_from_hpc(remote_path: str, local_path: str):
    """Copy file from HPC."""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    subprocess.run(
        ["scp", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
         f"{HPC_HOST}:{remote_path}", local_path],
        capture_output=True, check=True, timeout=300,
    )


# =============================================================================
# SLURM
# =============================================================================

def make_slurm_script(job_name: str, input_file: str, output_file: str) -> str:
    """Generate SLURM submission script for CP2K."""
    cores_per_node = 32
    n_nodes = max(1, -(-SLURM_NTASKS // cores_per_node))  # ceil division
    tasks_per_node = min(SLURM_NTASKS, cores_per_node)
    return f"""#!/bin/bash
#SBATCH -J {job_name}
#SBATCH -p {SLURM_PARTITION}
#SBATCH -N {n_nodes}
#SBATCH --ntasks-per-node={tasks_per_node}
#SBATCH -t {SLURM_WALLTIME}

{CP2K_ENV}

cd $SLURM_SUBMIT_DIR

echo "Job $SLURM_JOB_ID started at $(date)"
echo "Running on: $(scontrol show hostnames $SLURM_NODELIST | tr '\\n' ' ')"
echo "CP2K: {CP2K_EXE}"

mpirun -np {SLURM_NTASKS} {CP2K_EXE} -i {input_file} -o {output_file}

echo "Job $SLURM_JOB_ID finished at $(date)"
"""


def submit_slurm_job(remote_dir: str, slurm_script: str) -> str:
    """Submit SLURM job, return job ID."""
    # Write slurm script on HPC
    escaped = slurm_script.replace("'", "'\\''")
    ssh_cmd(f"cat > {remote_dir}/run.slurm << 'SLURM_EOF'\n{slurm_script}\nSLURM_EOF")

    # Submit
    result = ssh_cmd(f"cd {remote_dir} && sbatch run.slurm 2>&1")
    output = result.stdout.strip()
    if "Submitted batch job" in output:
        return output.split()[-1]
    raise RuntimeError(f"sbatch failed: {output}")


def check_job_status(job_id: str) -> str:
    """Check SLURM job status: RUNNING, COMPLETED, FAILED, CANCELLED, PENDING."""
    result = ssh_cmd(
        f"sacct -j {job_id} --format=State --noheader 2>/dev/null",
        check=False,
    )
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            state = line.strip().split()[0].strip()
            if state in ("RUNNING", "PENDING", "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT"):
                return state
    return "UNKNOWN"


def wait_for_job(job_id: str, poll_interval: int = 30) -> str:
    """Poll SLURM job until completion."""
    print(f"  Waiting for job {job_id} (poll every {poll_interval}s)...")
    while True:
        status = check_job_status(job_id)
        if status == "COMPLETED":
            print(f"  Job {job_id} COMPLETED")
            return "COMPLETED"
        elif status in ("FAILED", "CANCELLED", "TIMEOUT"):
            print(f"  Job {job_id} {status}")
            return status
        else:
            print(f"  Job {job_id}: {status}...", end="\r")
            time.sleep(poll_interval)


# =============================================================================
# Workflow steps
# =============================================================================

def setup_directories():
    """Create local output directories."""
    AIMD_DIR.mkdir(parents=True, exist_ok=True)
    DFT_DIR.mkdir(parents=True, exist_ok=True)


def generate_aimd_inputs() -> dict:
    """Step 1: Generate AIMD NVT inputs from CIF."""
    print("\n[Step 1] Generate AIMD NVT inputs")

    cell_abc, xyz_lines, element_counts = read_cif_to_xyz(str(CIF_FILE))
    natoms = len(xyz_lines)

    params = dict(AIMD_PARAMS)
    params["cell_a"], params["cell_b"], params["cell_c"] = cell_abc.split()
    params["coord_file"] = "structure.xyz"

    inp_content = generate_input(params, "aimd_nvt")
    xyz_content = write_xyz(natoms, "H2O box from CIF", xyz_lines)

    inp_path = AIMD_DIR / "aimd_nvt.inp"
    xyz_path = AIMD_DIR / "structure.xyz"
    inp_path.write_text(inp_content)
    xyz_path.write_text(xyz_content)

    print(f"  Generated: {inp_path}")
    print(f"  Generated: {xyz_path}")
    print(f"  Atoms: {natoms}, Elements: {element_counts}")
    print(f"  Cell: {cell_abc}")
    print(f"  Params: steps={params['steps']}, T={params['temperature']}K, dt={params['timestep']}fs")

    return {"natoms": natoms, "element_counts": element_counts, "cell_abc": cell_abc}


def check_aimd_completion() -> dict:
    """Step 2: Check AIMD completion by parsing local log file."""
    print("\n[Step 2] Check AIMD completion")

    log_path = AIMD_DIR / "H2O_aimd_nvt.log"
    result = {"converged": False, "md_steps": 0}

    if not log_path.exists():
        print(f"  Log file not found: {log_path}")
        return result

    parser = CP2KParser()
    parsed = parser.parse(str(log_path))
    result["converged"] = parsed.converged
    result["final_energy"] = parsed.final_energy
    result["job_type"] = parsed.job_type
    result["errors"] = parsed.errors
    result["warnings"] = parsed.warnings
    result["md_steps"] = parsed.metadata.get("md_steps", 0)
    result["scf_converged_steps"] = parsed.metadata.get("scf_converged_steps", 0)

    print(f"  Converged: {parsed.converged}")
    print(f"  Job type: {parsed.job_type}")
    print(f"  Final energy: {parsed.final_energy}")
    print(f"  MD steps: {result['md_steps']}")

    if parsed.errors:
        print(f"  Errors: {parsed.errors}")

    # Parse .ener
    ener_path = AIMD_DIR / "H2O_aimd_nvt-1.ener"
    if ener_path.exists():
        ener_data = parser.parse_ener(str(ener_path))
        result["ener_data"] = {
            "num_steps": len(ener_data["steps"]),
            "final_temperature": ener_data["temperature"][-1] if ener_data["temperature"] else None,
            "final_potential": ener_data["potential"][-1] if ener_data["potential"] else None,
        }
        print(f"  Ener steps: {result['ener_data']['num_steps']}")
        print(f"  Final temp: {result['ener_data']['final_temperature']} K")

    # Parse trajectory
    traj_path = AIMD_DIR / "H2O_aimd_nvt-pos-1.xyz"
    if traj_path.exists():
        frames = parser.parse_trajectory(str(traj_path))
        result["trajectory_frames"] = len(frames)
        print(f"  Trajectory frames: {len(frames)}")

    return result


def upload_aimd_to_hpc():
    """Upload AIMD inputs to HPC."""
    print("\n[Upload] AIMD inputs to HPC")

    remote_dir = f"{REMOTE_BASE}/aimd"
    ssh_cmd(f"mkdir -p {remote_dir}")

    for fname in ["aimd_nvt.inp", "structure.xyz"]:
        local = AIMD_DIR / fname
        if local.exists():
            scp_to_hpc(str(local), f"{remote_dir}/{fname}")
            print(f"  Uploaded: {fname}")

    return remote_dir


def submit_aimd(remote_dir: str) -> str:
    """Submit AIMD SLURM job."""
    print("\n[Submit] AIMD NVT job")

    slurm = make_slurm_script("H2O_aimd", "aimd_nvt.inp", "H2O_aimd_nvt.log")
    job_id = submit_slurm_job(remote_dir, slurm)
    print(f"  Job ID: {job_id}")

    # Save job id locally
    (AIMD_DIR / "job_id.txt").write_text(job_id)
    return job_id


def download_aimd_results(remote_dir: str):
    """Download AIMD outputs from HPC."""
    print("\n[Download] AIMD results from HPC")

    files = [
        "H2O_aimd_nvt.log",
        "H2O_aimd_nvt-1.ener",
        "H2O_aimd_nvt-pos-1.xyz",
        "H2O_aimd_nvt-1.restart",
    ]
    for fname in files:
        try:
            scp_from_hpc(f"{remote_dir}/{fname}", str(AIMD_DIR / fname))
            print(f"  Downloaded: {fname}")
        except Exception as e:
            print(f"  Skipped: {fname} ({e})")


def extract_last_frame_step() -> str:
    """Step 3: Extract last frame from AIMD trajectory."""
    print("\n[Step 3] Extract last frame")

    traj_path = AIMD_DIR / "H2O_aimd_nvt-pos-1.xyz"
    if not traj_path.exists():
        raise FileNotFoundError(f"Trajectory not found: {traj_path}")

    traj_content = traj_path.read_text()
    last_frame = extract_last_frame(traj_content)

    output_path = DFT_DIR / "last_frame.xyz"
    output_path.write_text(last_frame)

    lines = last_frame.strip().split("\n")
    natoms = int(lines[0])
    print(f"  Extracted {natoms} atoms to {output_path}")
    print(f"  Comment: {lines[1].strip()}")

    return str(output_path)


def generate_energy_inputs(coord_file: str) -> dict:
    """Step 4: Generate DFT single point inputs."""
    print("\n[Step 4] Generate DFT single point inputs")

    cell_abc, xyz_lines, element_counts = read_cif_to_xyz(str(CIF_FILE))

    params = dict(ENERGY_PARAMS)
    params["cell_a"], params["cell_b"], params["cell_c"] = cell_abc.split()
    params["coord_file"] = os.path.basename(coord_file)

    inp_content = generate_input(params, "energy")
    inp_path = DFT_DIR / "energy.inp"
    inp_path.write_text(inp_content)

    print(f"  Generated: {inp_path}")
    print(f"  Coord file: {params['coord_file']}")
    print(f"  Cell: {cell_abc}")

    return {"element_counts": element_counts, "cell_abc": cell_abc}


def check_energy_completion() -> dict:
    """Step 5: Check DFT energy completion."""
    print("\n[Step 5] Check DFT energy completion")

    log_path = DFT_DIR / "H2O_energy.log"
    result = {"converged": False}

    if not log_path.exists():
        print(f"  Log file not found: {log_path}")
        return result

    parser = CP2KParser()
    parsed = parser.parse(str(log_path))
    result["converged"] = parsed.converged
    result["final_energy"] = parsed.final_energy
    result["job_type"] = parsed.job_type
    result["errors"] = parsed.errors

    print(f"  Converged: {parsed.converged}")
    print(f"  Final energy: {parsed.final_energy}")

    return result


def upload_dft_to_hpc():
    """Upload DFT inputs to HPC."""
    print("\n[Upload] DFT inputs to HPC")

    remote_dir = f"{REMOTE_BASE}/dft_sp"
    ssh_cmd(f"mkdir -p {remote_dir}")

    for fname in ["energy.inp", "last_frame.xyz"]:
        local = DFT_DIR / fname
        if local.exists():
            scp_to_hpc(str(local), f"{remote_dir}/{fname}")
            print(f"  Uploaded: {fname}")

    return remote_dir


def submit_dft(remote_dir: str) -> str:
    """Submit DFT SLURM job."""
    print("\n[Submit] DFT energy job")

    slurm = make_slurm_script("H2O_energy", "energy.inp", "H2O_energy.log")
    job_id = submit_slurm_job(remote_dir, slurm)
    print(f"  Job ID: {job_id}")

    (DFT_DIR / "job_id.txt").write_text(job_id)
    return job_id


def download_dft_results(remote_dir: str):
    """Download DFT outputs from HPC."""
    print("\n[Download] DFT results from HPC")

    files = ["H2O_energy.log"]
    for fname in files:
        try:
            scp_from_hpc(f"{remote_dir}/{fname}", str(DFT_DIR / fname))
            print(f"  Downloaded: {fname}")
        except Exception as e:
            print(f"  Skipped: {fname} ({e})")


def generate_report(aimd_info: dict, aimd_result: dict, energy_result: dict):
    """Generate summary.json and report.md."""
    print("\n[Report] Generating summary")

    summary = {
        "workflow": "h2o_cp2k_aimd_to_dft",
        "hpc": {
            "host": HPC_HOST,
            "partition": SLURM_PARTITION,
            "cp2k_version": "v2025.1-oneapi2024",
            "ntasks": SLURM_NTASKS,
        },
        "structure": {
            "cif": str(CIF_FILE),
            "natoms": aimd_info.get("natoms"),
            "elements": aimd_info.get("element_counts"),
            "cell_abc": aimd_info.get("cell_abc"),
        },
        "aimd_nvt": {
            "params": AIMD_PARAMS,
            "converged": aimd_result.get("converged"),
            "final_energy": aimd_result.get("final_energy"),
            "md_steps": aimd_result.get("md_steps"),
            "errors": aimd_result.get("errors", []),
        },
        "dft_energy": {
            "params": ENERGY_PARAMS,
            "converged": energy_result.get("converged"),
            "final_energy": energy_result.get("final_energy"),
            "errors": energy_result.get("errors", []),
        },
    }

    summary_path = SCRIPT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"  Summary: {summary_path}")

    # report.md
    lines = [
        "# H2O CP2K Workflow Report",
        "",
        "## HPC Environment",
        f"- Host: `{HPC_HOST}`",
        f"- Partition: `{SLURM_PARTITION}`",
        f"- CP2K: v2025.1-oneapi2024",
        f"- MPI tasks: {SLURM_NTASKS}",
        "",
        "## Structure",
        f"- CIF: `{CIF_FILE.name}`",
        f"- Atoms: {aimd_info.get('natoms')}",
        f"- Elements: {aimd_info.get('element_counts')}",
        f"- Cell: {aimd_info.get('cell_abc')} A",
        "",
        "## AIMD NVT",
        f"- Steps: {AIMD_PARAMS['steps']}",
        f"- Timestep: {AIMD_PARAMS['timestep']} fs",
        f"- Temperature: {AIMD_PARAMS['temperature']} K",
        f"- Converged: {aimd_result.get('converged')}",
        f"- Final energy: {aimd_result.get('final_energy')} a.u.",
        f"- MD steps completed: {aimd_result.get('md_steps')}",
    ]
    if aimd_result.get("errors"):
        lines.append(f"- Errors: {aimd_result['errors']}")

    lines.extend([
        "",
        "## DFT Single Point",
        f"- Converged: {energy_result.get('converged')}",
        f"- Final energy: {energy_result.get('final_energy')} a.u.",
    ])
    if energy_result.get("errors"):
        lines.append(f"- Errors: {energy_result['errors']}")

    lines.extend(["", "---", "*Generated by SimFlow CP2K workflow*"])

    report_path = SCRIPT_DIR / "report.md"
    report_path.write_text("\n".join(lines))
    print(f"  Report: {report_path}")


# =============================================================================
# Main
# =============================================================================

def cmd_status():
    """Check status of submitted jobs."""
    print("=" * 60)
    print("H2O CP2K Workflow Status")
    print("=" * 60)

    # AIMD job
    aimd_job_file = AIMD_DIR / "job_id.txt"
    if aimd_job_file.exists():
        job_id = aimd_job_file.read_text().strip()
        status = check_job_status(job_id)
        print(f"\n  AIMD job {job_id}: {status}")
    else:
        print("\n  AIMD: no job submitted")

    # DFT job
    dft_job_file = DFT_DIR / "job_id.txt"
    if dft_job_file.exists():
        job_id = dft_job_file.read_text().strip()
        status = check_job_status(job_id)
        print(f"  DFT  job {job_id}: {status}")
    else:
        print("  DFT:  no job submitted")

    # Check local results
    aimd_result = check_aimd_completion()
    energy_result = check_energy_completion()

    if aimd_result.get("converged") and energy_result.get("converged"):
        print("\n  Both steps completed. Run with --submit to generate report.")


def cmd_submit():
    """Run full workflow with HPC submission."""
    print("=" * 60)
    print("H2O CP2K Workflow: AIMD NVT -> DFT Single Point")
    print(f"HPC: {HPC_HOST}, CP2K v2025.1-oneapi2024")
    print("=" * 60)

    setup_directories()

    # Check SSH connectivity
    print("\n[Check] SSH connectivity...")
    try:
        result = ssh_cmd("hostname", timeout=15)
        print(f"  Connected to: {result.stdout.strip()}")
    except Exception as e:
        print(f"  SSH connection failed: {e}")
        sys.exit(1)

    # === AIMD phase ===
    aimd_info = generate_aimd_inputs()
    aimd_result = check_aimd_completion()

    if not aimd_result.get("converged"):
        remote_aimd = upload_aimd_to_hpc()
        aimd_job_id = submit_aimd(remote_aimd)

        print(f"\n  AIMD job submitted: {aimd_job_id}")
        print(f"  Walltime: {SLURM_WALLTIME}")
        print(f"  Waiting for completion...")

        status = wait_for_job(aimd_job_id, poll_interval=30)
        if status != "COMPLETED":
            print(f"\n  AIMD job did not complete: {status}")
            # Try to download whatever output exists
            download_aimd_results(remote_aimd)
            # Check if log exists and parse
            aimd_result = check_aimd_completion()
            if not aimd_result.get("converged"):
                generate_report(aimd_info, aimd_result, {"converged": False})
                sys.exit(1)

        download_aimd_results(remote_aimd)
        aimd_result = check_aimd_completion()

    if not aimd_result.get("converged"):
        print("\n  AIMD did not converge. Aborting.")
        generate_report(aimd_info, aimd_result, {"converged": False})
        sys.exit(1)

    print(f"\n  AIMD converged! Energy: {aimd_result.get('final_energy')} a.u.")

    # === DFT phase ===
    coord_file = extract_last_frame_step()
    generate_energy_inputs(coord_file)

    remote_dft = upload_dft_to_hpc()
    dft_job_id = submit_dft(remote_dft)

    print(f"\n  DFT job submitted: {dft_job_id}")
    print(f"  Waiting for completion...")

    status = wait_for_job(dft_job_id, poll_interval=15)
    if status != "COMPLETED":
        print(f"\n  DFT job did not complete: {status}")
        download_dft_results(remote_dft)
        energy_result = check_energy_completion()
        generate_report(aimd_info, aimd_result, energy_result)
        sys.exit(1)

    download_dft_results(remote_dft)
    energy_result = check_energy_completion()

    # === Report ===
    generate_report(aimd_info, aimd_result, energy_result)

    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETE")
    print("=" * 60)
    print(f"\n  AIMD energy: {aimd_result.get('final_energy')} a.u.")
    print(f"  DFT  energy: {energy_result.get('final_energy')} a.u.")
    print(f"\n  Report: {SCRIPT_DIR / 'report.md'}")
    print(f"  Summary: {SCRIPT_DIR / 'summary.json'}")


def cmd_dry_run():
    """Generate inputs only, no HPC submission."""
    print("=" * 60)
    print("H2O CP2K Workflow: DRY RUN")
    print("=" * 60)

    setup_directories()

    aimd_info = generate_aimd_inputs()
    aimd_result = check_aimd_completion()

    # Generate DFT inputs if trajectory exists
    traj_path = AIMD_DIR / "H2O_aimd_nvt-pos-1.xyz"
    if traj_path.exists():
        coord_file = extract_last_frame_step()
        generate_energy_inputs(coord_file)
    else:
        print("\n  Trajectory not found, skipping DFT input generation")
        print("  (Will be generated after AIMD completes)")

    generate_report(aimd_info, aimd_result, {"converged": False})

    print("\n" + "=" * 60)
    print("DRY RUN COMPLETE")
    print("=" * 60)
    print(f"\nGenerated files:")
    print(f"  {AIMD_DIR}/aimd_nvt.inp")
    print(f"  {AIMD_DIR}/structure.xyz")
    if (DFT_DIR / "energy.inp").exists():
        print(f"  {DFT_DIR}/energy.inp")
    print(f"\nTo submit: python {__file__} --submit")


def main():
    parser = argparse.ArgumentParser(description="H2O CP2K AIMD -> DFT workflow")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Generate inputs only")
    group.add_argument("--submit", action="store_true", help="Submit to HPC and wait")
    group.add_argument("--status", action="store_true", help="Check job status")
    args = parser.parse_args()

    if not CIF_FILE.exists():
        print(f"CIF file not found: {CIF_FILE}")
        sys.exit(1)

    if args.dry_run:
        cmd_dry_run()
    elif args.submit:
        cmd_submit()
    elif args.status:
        cmd_status()


if __name__ == "__main__":
    main()
