# HPC Integration Guide

## Supported Schedulers

| Scheduler | Connector | Status |
|-----------|-----------|--------|
| SLURM | `slurm` | Implemented |
| PBS/Torque | `pbs` | Implemented |
| SSH | `ssh` | Implemented |
| Local | `local` | Implemented |

## SLURM

### Usage

```bash
# Generate SLURM script
simflow hpc prepare --job-name si_relax --executable vasp_std --nodes 2 --ntasks 32

# Validate script
simflow hpc dry_run --script-path job.sh

# Submit
simflow hpc submit --script-path job.sh --scheduler slurm

# Check status
simflow hpc status --job-id 12345 --scheduler slurm
```

### Environment

SLURM commands (`sbatch`, `squeue`, `scancel`) must be available in PATH.

## PBS/Torque

### Usage

```bash
simflow hpc submit --script-path job.sh --scheduler pbs
simflow hpc status --job-id 12345.pbs-server --scheduler pbs
```

### Requirements

- `qsub`, `qstat`, `qdel` commands available
- Script must contain `#PBS` directives (walltime, nodes)

## SSH Remote Execution

### Configuration

Set environment variables:

```bash
export SIMFLOW_SSH_HOST=hpc.university.edu
export SIMFLOW_SSH_USER=researcher
export SIMFLOW_SSH_KEY=~/.ssh/hpc_key
```

### Usage

```bash
simflow hpc submit --script-path job.sh --scheduler ssh
simflow hpc status --job-id 12345 --scheduler ssh
```

### How It Works

1. Script is copied to remote host via SCP
2. Executed via `nohup bash script.sh &`
3. PID is returned as job_id
4. Status checked via `kill -0 PID`

## Local Execution

For testing and small jobs:

```bash
simflow hpc submit --script-path job.sh --scheduler local
```

Executes `bash script.sh` as a subprocess with configurable timeout.

## Job Script Templates

### SLURM Template

```bash
#!/bin/bash
#SBATCH --job-name=simflow_job
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=16
#SBATCH --time=04:00:00
#SBATCH --output=job_%j.out
#SBATCH --error=job_%j.err

module load vasp/6.3.0
mpirun -np $SLURM_NTASKS vasp_std
```

### PBS Template

```bash
#!/bin/bash
#PBS -N simflow_job
#PBS -l nodes=1:ppn=16
#PBS -l walltime=04:00:00
#PBS -o job.out
#PBS -e job.err

cd $PBS_O_WORKDIR
module load vasp/6.3.0
mpirun -np 16 vasp_std
```

## Credential Security

- SSH credentials are read from environment variables only
- Never stored in files, artifacts, or logs
- Key file path is validated before use
- All SSH commands use `BatchMode=yes` to prevent interactive prompts
