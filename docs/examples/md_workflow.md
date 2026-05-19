# Classical MD Legacy Recipe Example

This is a legacy recipe example for classical molecular dynamics. It is
guidance for evidence tracking, not a fixed SimFlow executor or a `simflow-md`
CLI.

## Suggested Stage Mapping

| Research activity | Canonical stage |
| --- | --- |
| Review force field and system precedent | `literature_review` |
| Define ensemble, equilibration, production, and observables | `proposal` |
| Preserve/build the initial model and force-field provenance | `modeling` |
| Prepare inputs, dry-run, and gate submit | `computation` |
| Analyze trajectory, thermodynamics, RDF, MSD, and figures | `analysis_visualization` |
| Write methods, limitations, and claims | `writing` |

## Evidence To Record

- Initial structure and force-field provenance.
- LAMMPS or other engine input files, scripts, command, and environment.
- Dry-run report, input validation, resource estimate, credential scan, and
  script/input hashes.
- Gate decision id before real local, remote, or HPC execution.
- Trajectory files, analysis scripts, derived tables, figures, and claim map.

## Optional Helpers

The host agent may use LAMMPS helpers, MDAnalysis, OVITO, VMD, ASE, pandas,
matplotlib, or custom Python. SimFlow only requires that scripts, inputs,
outputs, environment, and lineage are recorded.

## Legacy Compatibility

`workflow/workflows/md.json` remains available and maps to the
`classical_md` recipe during migration. It is retained for compatibility with
older projects and tests, not as a mandatory top-level workflow.
