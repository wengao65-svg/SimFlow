# CP2K Common Parameters

This note is a SimFlow-maintained quick reference for common-task orchestration.
It is not a full CP2K parameter catalog.

## GLOBAL

- `PROJECT`: output name prefix
- `RUN_TYPE`: `ENERGY`, `GEO_OPT`, `CELL_OPT`, or `MD`
- `PRINT_LEVEL`: usually `LOW` for orchestration defaults

## FORCE_EVAL / DFT

- `BASIS_SET_FILE_NAME`: usually a symbolic library name such as `BASIS_MOLOPT`
- `POTENTIAL_FILE_NAME`: usually a symbolic library name such as `POTENTIAL`
- `CHARGE`
- `MULTIPLICITY`

## QS / MGRID / SCF / OT / XC

- `EPS_DEFAULT`
- `CUTOFF`
- `REL_CUTOFF`
- `MAX_SCF`
- `EPS_SCF`
- `SCF_GUESS`
- `MINIMIZER`
- `PRECONDITIONER`
- `XC_FUNCTIONAL`

These are the minimum common-task knobs that SimFlow validates for the CP2K orchestration layer.

## SUBSYS

- `CELL`
- `TOPOLOGY`
  - `COORD_FILE_NAME`
  - `COORD_FILE_FORMAT`
- `KIND` blocks for every element present in the structure

## MOTION

For common SimFlow coverage:

- `ENERGY`: no `MOTION`
- `GEO_OPT`: `MOTION / GEO_OPT`
- `CELL_OPT`: `MOTION / CELL_OPT`
- `AIMD`: `MOTION / MD`

## Restart / Continuation

- `EXT_RESTART / RESTART_FILE_NAME`
- `SCF_GUESS RESTART`

SimFlow only checks restart intent and referenced file presence. It does not expose the full restart control surface.
