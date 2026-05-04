#!/bin/bash
# Run a single VASP step on HPC.
# Usage: ./run_step.sh <step>
#   step: relax, scf, or bands
#
# Inter-step file passing:
#   relax → CONTCAR → scf/POSCAR, bands/POSCAR
#   scf   → WAVECAR,CHGCAR → bands/

set -e

STEP=${1:?Usage: $0 <relax|scf|bands>}
HPC_HOST="${SIMFLOW_HPC_HOST:-hpc}"
HPC_BASE="${SIMFLOW_HPC_BASE:?Error: SIMFLOW_HPC_BASE not set}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Si DFT Step: ${STEP} ==="

# Validate inputs
echo "Validating inputs..."
python3 "${SCRIPT_DIR}/validate_inputs.py"

# Create HPC directory
echo "Creating HPC directory..."
ssh ${HPC_HOST} "mkdir -p ${HPC_BASE}/${STEP}"

# Upload files
echo "Uploading files to HPC..."
scp "${SCRIPT_DIR}/${STEP}/INCAR" "${SCRIPT_DIR}/${STEP}/KPOINTS" \
    "${SCRIPT_DIR}/${STEP}/POSCAR" "${SCRIPT_DIR}/${STEP}/POTCAR" \
    "${SCRIPT_DIR}/${STEP}/vasp.slurm" \
    ${HPC_HOST}:${HPC_BASE}/${STEP}/

# Submit job
echo "Submitting SLURM job..."
JOB_ID=$(ssh ${HPC_HOST} "cd ${HPC_BASE}/${STEP} && sbatch vasp.slurm" | awk '{print $NF}')
echo "Job ID: ${JOB_ID}"

# Wait for completion
echo "Waiting for job ${JOB_ID}..."
while true; do
    STATUS=$(ssh ${HPC_HOST} "sacct -j ${JOB_ID} --format=State --noheader 2>/dev/null" | head -1 | tr -d ' ')
    case "${STATUS}" in
        COMPLETED*)
            echo "Job completed!"
            break
            ;;
        FAILED*|CANCELLED*|TIMEOUT*)
            echo "Job failed: ${STATUS}"
            exit 1
            ;;
        *)
            echo "Status: ${STATUS}..."
            sleep 30
            ;;
    esac
done

# Download results
echo "Downloading results..."
mkdir -p "${SCRIPT_DIR}/${STEP}/output"
DOWNLOAD_FILES="OUTCAR OSZICAR CONTCAR vasprun.xml"
if [ "${STEP}" = "scf" ]; then
    DOWNLOAD_FILES="${DOWNLOAD_FILES} WAVECAR CHGCAR"
fi
for f in ${DOWNLOAD_FILES}; do
    scp ${HPC_HOST}:${HPC_BASE}/${STEP}/${f} "${SCRIPT_DIR}/${STEP}/output/" 2>/dev/null || true
done

# Check convergence
if [ -f "${SCRIPT_DIR}/${STEP}/output/OUTCAR" ]; then
    if grep -q "reached required accuracy" "${SCRIPT_DIR}/${STEP}/output/OUTCAR"; then
        echo "Converged!"
    else
        echo "WARNING: May not have converged"
    fi
fi

# Inter-step file passing
if [ "${STEP}" = "relax" ]; then
    echo "Passing relaxed structure to next steps..."
    if [ -f "${SCRIPT_DIR}/relax/output/CONTCAR" ]; then
        cp "${SCRIPT_DIR}/relax/output/CONTCAR" "${SCRIPT_DIR}/scf/POSCAR"
        cp "${SCRIPT_DIR}/relax/output/CONTCAR" "${SCRIPT_DIR}/bands/POSCAR"
        echo "  Copied CONTCAR → scf/POSCAR, bands/POSCAR"
    fi
elif [ "${STEP}" = "scf" ]; then
    echo "Passing charge density to bands step..."
    for f in WAVECAR CHGCAR; do
        if [ -f "${SCRIPT_DIR}/scf/output/${f}" ]; then
            cp "${SCRIPT_DIR}/scf/output/${f}" "${SCRIPT_DIR}/bands/${f}"
            echo "  Copied ${f} → bands/${f}"
        fi
    done
fi

echo "=== ${STEP} complete ==="
