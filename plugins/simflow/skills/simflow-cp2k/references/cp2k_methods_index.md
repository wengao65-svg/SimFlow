# CP2K Methods Index

This is a lightweight SimFlow index for common CP2K workflow methods.
It exists to steer orchestration decisions, not to mirror the full CP2K manual.

## Covered by simflow-cp2k

- `ENERGY`
  - Use for single-point electronic energy evaluation on a fixed structure.
- `GEO_OPT`
  - Use for common atomic relaxation with fixed cell.
- `CELL_OPT`
  - Use for basic simultaneous cell and structure relaxation.
- `MD` with `NVT`
  - Use for thermostat-controlled AIMD at a target temperature.
- `MD` with `NVE`
  - Use for short microcanonical AIMD segments after equilibration.
- `MD` with basic `NPT`
  - Use for isotropic pressure/temperature control in simple workflows.
- Restart / continuation
  - Use when a prior CP2K restart artifact is available and the continuation intent is clear.

## Covered by Validation

- `GLOBAL / RUN_TYPE`
- `FORCE_EVAL / DFT`
- `BASIS_SET_FILE_NAME`
- `POTENTIAL_FILE_NAME`
- `MGRID`
- `SCF`
- `OT`
- `XC`
- `SUBSYS / CELL / TOPOLOGY`
- task-appropriate `MOTION` sections
- `KIND` coverage against referenced coordinates
- coordinate file existence
- restart file existence

## Covered by Parsing

- `.log`
- `*.ener`
- `*-pos-1.xyz`
- `.restart` metadata

## Not Covered

- Exhaustive CP2K method families
- Full basis/potential selection guidance
- Specialized advanced workflows such as metadynamics, constrained MD, NEB, replica exchange, or hybrid-functional tuning
- Real HPC submission logic
