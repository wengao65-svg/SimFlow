# Software Skills Reference

Software skills are optional domain assistants. They provide input-file
guidance, common checks, troubleshooting notes, template examples, official
documentation pointers, and artifact registration suggestions.

They are not workflow executors. They must not make a fixed parser, builder,
report name, software package, or DFT/AIMD/MD path mandatory.

## VASP

`simflow-vasp` can help with common VASP setup, validation, output inspection,
and troubleshooting. It may suggest py4vasp, VASPKIT, SimFlow parsers, or custom
Python, but none of those is the only valid path.

Unknown or specialized requests such as phonon, NEB, SOC, hybrid, DFT+U,
defect, surface, adsorption, and custom analysis should return candidates and
missing information instead of silently becoming a static calculation.

POTCAR content is licensed/proprietary in many installations. SimFlow must not
generate, copy, print, store, or redistribute it.

Optional helper script:

```bash
python skills/simflow-vasp/scripts/orchestrate_vasp_task.py \
  --task "plan VASP NEB calculation" \
  --project-root /path/to/project \
  --calc-dir ./neb
```

The script writes reports and artifacts under `.simflow/` only when given a
project root. It does not submit jobs and does not advance a fixed VASP
workflow.

## CP2K

`simflow-cp2k` can help inspect CP2K input/output, common Quickstep/AIMD setup
questions, validation risks, and handoff notes. Unknown requests should remain
open and record uncertainty.

## LAMMPS

`simflow-lammps` can assist with data/input scripts, force-field provenance,
trajectory analysis, and common MD checks. It must not treat every unknown
request as a fixed MD alias.

## Unsupported Placeholders

`simflow-qe` and `simflow-gaussian` are reserved placeholders in the current
product build. They should state that QE/Gaussian support is unavailable, avoid
generating engine-specific inputs or validation claims, and only record
user-provided files as generic artifacts when traceability is requested.

## Analysis Helpers

Built-in parsers and plotting scripts are optional. The host agent may also use
self-written Python, pandas, matplotlib, ASE, pymatgen, MDAnalysis, py4vasp,
notebooks, or other appropriate tools.

The hard requirement is traceability:

- script or command recorded
- input files recorded
- output files recorded
- environment or package assumptions recorded
- artifact lineage linked
- incomplete or speculative conclusions labeled
