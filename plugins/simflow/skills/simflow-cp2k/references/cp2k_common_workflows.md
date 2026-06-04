# CP2K Common Workflows

This summary captures the common-task layer that `simflow-cp2k` orchestrates.
For portable setup and execution-boundary examples, load `cp2k_example_patterns.md`. For official-source navigation and broader workflows, load `cp2k_official_sources.md` and `cp2k_task_checklists.md`.

## Single Point Energy

- Typical intent: evaluate the electronic energy of a prepared structure.
- Expected core sections:
  - `GLOBAL / RUN_TYPE ENERGY`
  - `FORCE_EVAL / DFT`
  - `SUBSYS / CELL`
  - `SUBSYS / TOPOLOGY`
  - `KIND`
- SimFlow outputs:
  - input manifest
  - validation report
  - dry-run compute plan
  - optional analysis report if outputs exist
- Required caution:
  - do not claim grid, SCF, force, or stress convergence without evidence

## Geometry Optimization

- Typical intent: relax atomic positions with fixed cell.
- Expected addition:
  - `MOTION / GEO_OPT`
- SimFlow checks:
  - `RUN_TYPE GEO_OPT`
  - `MOTION / GEO_OPT` consistency
  - `KIND` coverage and coordinate file presence
- Evidence:
  - optimized status requires CP2K output criteria, not just a restart or final coordinate file

## Basic Cell Optimization

- Typical intent: relax both atomic positions and cell parameters in a simple workflow.
- Expected addition:
  - `MOTION / CELL_OPT`
- SimFlow scope:
  - basic optimizer and external pressure fields only
  - no attempt to model the full CP2K cell-optimization option space
- Required caution:
  - check stress/grid sensitivity and pressure units before interpreting results

## AIMD NVT / NVE / Basic NPT

- Typical intent: short to moderate common-ensemble AIMD setup.
- Expected addition:
  - `RUN_TYPE MD`
  - `MOTION / MD`
- Ensemble assumptions:
  - `NVT`: thermostat-controlled
  - `NVE`: no thermostat section required
  - basic `NPT`: simple isotropic pressure/temperature control
- Evidence:
  - inspect `.ener` for equilibration, temperature, conserved quantity, and drift
  - separate equilibration and production before analysis

## Restart / Continuation

- Typical intent: continue from an existing restart artifact.
- Expected indicators:
  - `EXT_RESTART / RESTART_FILE_NAME`
  - or `SCF_GUESS RESTART`
- SimFlow checks:
  - referenced restart file exists
  - restart intent is visible in the input deck
  - dry-run plan still stays non-submitting
- Required caution:
  - clarify whether the continuation is SCF, geometry/cell optimization, MD, or a higher-level workflow

## Parse / Troubleshoot

- Typical intent: inspect outputs without running CP2K.
- Expected sources:
  - `.log`
  - `*.ener`
  - `*-pos-1.xyz`
  - `.restart`
- SimFlow extracts:
  - CP2K version
  - run type
  - project name
  - SCF convergence indicators
  - normal end or abort
  - final energy
  - MD steps
  - temperature
  - conserved quantity
  - used time
  - last frame
- Required caution:
  - final energy alone is not proof of successful completion
