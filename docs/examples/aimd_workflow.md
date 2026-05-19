# AIMD Legacy Recipe Example

This is a legacy recipe example for ab initio molecular dynamics. It describes
typical evidence and risks, not a required SimFlow executor or a `simflow-aimd`
CLI.

## Suggested Stage Mapping

| Research activity | Canonical stage |
| --- | --- |
| Review AIMD settings or comparable systems | `literature_review` |
| Define ensemble, timestep, temperature, and run length | `proposal` |
| Preserve/build initial configuration | `modeling` |
| Prepare inputs, dry-run, and gate submit | `computation` |
| Analyze trajectory, temperature, RDF, MSD, and figures | `analysis_visualization` |
| Write caveats, methods, and result claims | `writing` |

## Evidence To Record

- Initial structure or trajectory source artifact.
- Thermostat, timestep, ensemble, pseudopotential/basis, and software rationale.
- Input files, scripts, command, environment, and hashes.
- Dry-run report, resource estimate, input validation, and credential scan.
- Approval gate decision before real execution.
- Trajectory completeness, equilibration notes, analysis scripts, derived data,
  figures, and claim-evidence map.

## Optional Helpers

The host agent may use VASP, CP2K, QE, ASE, pymatgen, MDAnalysis, py4vasp,
pandas, matplotlib, custom Python, or another suitable path. SimFlow requires
traceability, not a specific parser or plotting library.

## Legacy Compatibility

`workflow/workflows/aimd.json` remains available for migration and recipe
loading. It should be treated as a compatibility source, not as the canonical
workflow contract for all AIMD work.
