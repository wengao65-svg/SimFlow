# CP2K Parameter Policies

This note is a SimFlow-maintained quick reference for common-task orchestration and review. It is not a full CP2K parameter catalog. Verify exact keyword meanings, defaults, units, and allowed values in the CP2K manual when a parameter affects scientific conclusions.

## GLOBAL

- `PROJECT`: output name prefix. Record it because CP2K output files commonly inherit it.
- `RUN_TYPE`: common SimFlow helper coverage includes `ENERGY`, `GEO_OPT`, `CELL_OPT`, and `MD`.
- `PRINT_LEVEL`: `LOW` is a quiet default, but `MEDIUM` or task-specific print keys may be needed for diagnostics.

`RUN_TYPE` must agree with `MOTION` sections. `ENERGY` should not include optimization or MD motion sections. `GEO_OPT`, `CELL_OPT`, and `MD` require the corresponding `MOTION` subsection.

## FORCE_EVAL / DFT

- `METHOD`: usually `QS` for Quickstep DFT in the helper-supported path.
- `BASIS_SET_FILE_NAME`: may be a library name or path. Record the name/path but do not copy library content.
- `POTENTIAL_FILE_NAME`: may be a library name or path. Record the name/path but do not copy library content.
- `CHARGE` and `MULTIPLICITY`: require user confirmation when chemically ambiguous.

Basis and potential choices are scientific assumptions. Do not silently swap functional families, potential charges, or basis quality. For generated inputs, verify every element has a matching `KIND` block.

## QS

- `EPS_DEFAULT`: affects numerical thresholds and can matter for force quality, MD drift, and geometry convergence.
- `EXTRAPOLATION` and `EXTRAPOLATION_ORDER`: important for MD continuation and density guesses.

For MD, inspect whether the extrapolation strategy matches the continuity of the trajectory. For discontinuous changes, restarts, or changed particle number, be conservative and ask for intent.

## MGRID

- `CUTOFF`: controls the finest real-space grid cutoff.
- `REL_CUTOFF`: controls mapping of Gaussian products to grid levels.
- `NGRIDS` and progression settings can matter for advanced convergence review.

Do not treat default `CUTOFF` and `REL_CUTOFF` as converged. For production work, record convergence evidence or state that it is missing. Geometry, cell, phonon, and MD workflows require force/stress-quality consideration, not just total-energy stability.

## SCF / OT / diagonalization

- `MAX_SCF`, `EPS_SCF`, `SCF_GUESS`, `OUTER_SCF`, OT settings, diagonalization settings, mixing, smearing, and added MOs should match the electronic structure problem.
- OT-style defaults may be suitable for many insulating molecular/condensed systems but are not universal.
- Metallic, magnetic, charged, small-gap, or difficult systems may need diagonalization, smearing, mixing, or user-confirmed advanced choices.

Report SCF convergence from output evidence. Do not infer convergence from final energy alone.

## XC

- `XC_FUNCTIONAL` and any dispersion, hybrid, meta-GGA, or post-HF settings should be source-backed and recorded.
- Advanced methods such as hybrid functionals, GW, RPA, MP2, DFTB, xTB, and ML potentials require method-specific references and should not be forced into the common helper path.

## SUBSYS

- `CELL`: record cell vectors or ABC values, periodicity, vacuum, and whether stress/cell optimization matters.
- `TOPOLOGY`: record `COORD_FILE_NAME` and `COORD_FILE_FORMAT` when coordinates are external.
- `COORD`: inline coordinates are valid; parse and verify element coverage when present.
- `KIND`: require a block for every element or kind label present in the structure. Record basis and potential names for each.

The current SimFlow validation helper focuses on external coordinate files and common DFT/QS decks. For inline `COORD` or advanced topology, inspect manually and record the helper limitation.

## MOTION

For common SimFlow coverage:

- `ENERGY`: no `MOTION`.
- `GEO_OPT`: `MOTION/GEO_OPT` with optimizer, thresholds, constraints, and restart printing.
- `CELL_OPT`: `MOTION/CELL_OPT` with pressure, cell degrees of freedom, symmetry, and stress-quality review.
- `AIMD`: `MOTION/MD` with ensemble, timestep, steps, thermostat/barostat, initialization, output cadence, and restart policy.

For MD, record whether the requested calculation is equilibration, production, NVE drift testing, or a continuation.

## Restart / continuation

- `EXT_RESTART/RESTART_FILE_NAME`
- `EXT_RESTART/RESTART_COUNTERS`
- `SCF_GUESS RESTART`
- CP2K-generated restart input files such as `PROJECT-1.restart`

SimFlow checks restart intent and referenced file presence for the common path. Manual review is required for velocities, thermostat/barostat state, counters, project names, changed inputs, and continuation semantics.
