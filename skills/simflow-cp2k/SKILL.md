# SimFlow CP2K -- CP2K input generation and output parsing

## Trigger conditions

- User requests CP2K calculation setup (AIMD, DFT single point, geometry optimization)
- User provides CIF/XYZ structure and asks for CP2K input files
- User asks to parse CP2K output files (.log, .ener, trajectory)

## Input conditions

- CIF or XYZ structure file
- Calculation type: aimd_nvt, energy, geo_opt
- Optional: parameter overrides (cutoff, temperature, steps, etc.)

## Output artifacts

- `.inp` -- CP2K input file
- `structure.xyz` -- converted structure in XYZ format
- `submit.slurm` -- SLURM submission script (optional)

## Status write rules

- On input generation success: write `parameters` to stage metadata
- On parse completion: write `converged`, `final_energy`, `job_type` to state

## Checkpoint rules

- Checkpoint after input generation
- Checkpoint after output parsing

## Validation items

- CIF file exists and is readable
- Cell parameters extracted correctly
- At least one atom in structure
- CP2K input has valid GLOBAL section
- RUN_TYPE matches requested job type

## Prohibited actions

- Do not modify user's CIF file
- Do not hardcode HPC credentials or paths
- Do not submit without explicit approval

## Manual confirmation scenarios

- Real HPC submission requires approval gate
- Large systems (>1000 atoms) should warn about cost
