# DFT Legacy Recipe Example

This is a legacy recipe example. It illustrates the evidence that a silicon DFT
study might record, but it is not a mandatory SimFlow executor path and does
not imply that a `simflow-dft` CLI exists.

## Suggested Stage Mapping

| Research activity | Canonical stage |
| --- | --- |
| Review prior Si calculations | `literature_review` |
| Decide relaxation/SCF/bands/DOS scope | `proposal` |
| Preserve or transform the Si structure | `modeling` |
| Prepare inputs, dry-run, and gate submit | `computation` |
| Parse outputs and plot bands/DOS | `analysis_visualization` |
| Draft methods/results or handoff notes | `writing` |

## Evidence To Record

- Source structure artifact, for example a user-provided CIF or POSCAR.
- Calculation manifest explaining relaxation, SCF, bands, or DOS intent.
- Input files or input-generation script, including hashes.
- Input validation report and resource estimate.
- Dry-run report and credential scan before any real submit.
- Gate decision id for real local, remote, or HPC execution.
- Output artifacts, parser/custom analysis scripts, figures, and claim map.

## Optional Helpers

The host agent may use VASP, Quantum ESPRESSO, CP2K, ASE, pymatgen, py4vasp,
VASPKIT, custom Python, or another appropriate tool. SimFlow only requires that
the selected path is recorded with artifacts and lineage.

For VASP planning, the optional helper can be invoked directly:

```bash
python skills/simflow-vasp/scripts/orchestrate_vasp_task.py \
  --task "plan Si relaxation, SCF, band, and DOS calculations" \
  --project-root /path/to/project \
  --calc-dir .
```

This writes planning/validation artifacts. It does not submit jobs.

## Legacy Compatibility

`workflow/workflows/dft.json` remains loadable as a legacy workflow source and
is converted by runtime helpers into a `dft` recipe. New documentation and tests
should treat it as a recipe example, not as a fixed DAG that all DFT projects
must follow.
