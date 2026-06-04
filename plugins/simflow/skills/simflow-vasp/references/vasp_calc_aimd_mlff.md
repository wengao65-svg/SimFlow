# VASP Calculation Class: AIMD, Enhanced MD, and MLFF

Use this reference for ab-initio molecular dynamics, thermostat/barostat choices, constrained or biased MD, thermodynamic integration, and machine-learned force-field training/application in VASP.

## Official sources

- Molecular dynamics calculations: https://www.vasp.at/wiki/Molecular-dynamics_calculations
- MD tutorials: https://www.vasp.at/tutorials/latest/md/
- MDALGO: https://www.vasp.at/wiki/MDALGO
- TEBEG: https://www.vasp.at/wiki/TEBEG
- TEEND: https://www.vasp.at/wiki/TEEND
- SMASS: https://www.vasp.at/wiki/SMASS
- Machine learning force-field basics: https://www.vasp.at/wiki/Machine_learning_force_field_calculations
- MLFF best practices: https://www.vasp.at/wiki/Best_practices_for_machine-learned_force_fields

## Minimum evidence

- Ensemble, temperature/pressure schedule, timestep, total length, equilibration/production boundary, and output cadence.
- Starting structure provenance and whether the calculation is an ab-initio MD, MLFF training, MLFF refit, or MLFF production run.
- Statistical plan for RDF/MSD/diffusion/viscosity/phase behavior/transport claims.

## Tags and files to inspect

- `IBRION=0`, `NSW`, `POTIM`, `TEBEG`, `TEEND`, `MDALGO`, `SMASS`, `ISIF`, thermostat/barostat tags, restart tags.
- `XDATCAR`, `OUTCAR`, `OSZICAR`, `vasprun.xml`, `vaspout.h5`, restart files.
- MLFF: `ML_LMLFF`, `ML_MODE`, `ML_AB`, `ML_FFN`, `ML_LOGFILE`, and `ML_*` tags.

## SimFlow guidance

- AIMD and MLFF training are high-cost compute; require dry-run evidence and approval gates before real execution.
- Separate equilibration from production in reports and figures.
- Record uncertainty estimates, time origins, sampling interval, unit conversions, and discarded transient.
- For MLFF, record training database provenance, test errors, active-learning decisions, and prediction-only vs ab-initio steps.

## Common risks

- Treating short or unequilibrated trajectories as production statistics.
- Ignoring energy/temperature drift or thermostat/barostat artifacts.
- Reusing MLFF outside its training domain.
- Missing MPI/core pinning or resource notes for MLFF workloads.
