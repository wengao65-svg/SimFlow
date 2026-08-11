# Software Skills Reference

Software skills are optional Domain Skills. They provide input-file guidance,
common checks, troubleshooting notes, examples, and official-documentation
pointers.

They are not workflow executors. They must not make a fixed parser, builder,
report name, software package, or DFT/AIMD/MD path mandatory.

## VASP

`simflow-vasp` can help with common VASP setup, validation, output inspection,
and troubleshooting. It may suggest py4vasp, VASPKIT, SimFlow parsers, or custom
Python, but none of those is the only valid path.

Unknown or specialized requests such as phonon, NEB, SOC, hybrid, DFT+U,
defect, surface, adsorption, and custom analysis should return candidates and
missing information instead of silently becoming a static calculation.

POTCAR content is licensed/proprietary in many installations. SimFlow may use a
configured user-owned library to materialize POTCAR inside a controlled local
calculation directory, using fixed ASE setup tables for variant selection and
SimFlow runtime code for all restricted file access. It must never return,
print, place in the normal artifact store, commit, package, or redistribute the
content.

Optional helper script:

```bash
python skills/simflow-vasp/scripts/orchestrate_vasp_task.py \
  --task "plan VASP NEB calculation" \
  --project-root /path/to/project \
  --calc-dir ./neb
```

The script does not submit jobs and does not advance a fixed VASP workflow.

Helpers remain usable without SimFlow MCP or workflow state. Runtime recording,
when explicitly requested by a caller, is a separate adapter concern.

## CP2K

`simflow-cp2k` can help inspect CP2K input/output, common Quickstep/AIMD setup
questions, validation risks, and handoff notes. Unknown requests should remain
open and record uncertainty.

## LAMMPS

`simflow-lammps` can assist with data/input scripts, force-field provenance,
trajectory analysis, and common MD checks. It must not treat every unknown
request as a fixed MD alias.

## GPUMD/NEP

`simflow-gpumd` is the GPUMD/NEP ecosystem Domain Assistant. It owns NEP
trainer files and GPUMD MD inputs, outputs, version-sensitive behavior, task
guidance, and troubleshooting. Its optional helpers currently support input
generation, input validation, compute planning, orchestration, static input
inspection, manifest generation, selected output parsing, and evidence
handoff. Real execution and submit remain outside helper support.

## Machine-Learning Potentials

`simflow-mlp` is a cross-tool Domain Assistant. It owns dataset, labeling,
training-evidence, validation, active-learning, deployment, and
production-readiness methodology without prescribing one trainer's
implementation. Provider files and configuration syntax remain with the
relevant software Domain Assistant.

Domain Assistant, helper support level, and helper-evidence output are distinct
concepts. `workflow/toolchains/capabilities.json` is the support-level source of
truth. Optional scripts may emit `simflow.helper_evidence.v1` records without
turning that output format into a product category.

## Unsupported Engines

Unsupported engines do not receive placeholder Skills. The router should retain
the software name as context, select the relevant Research Task Skill, and avoid
claiming built-in engine support.

## Analysis Helpers

Built-in parsers and plotting scripts are optional. The host agent may also use
self-written Python, pandas, matplotlib, ASE, pymatgen, MDAnalysis, py4vasp,
notebooks, or other appropriate tools.

The scientific requirement is reproducibility:

- script or command recorded
- input files recorded
- output files recorded
- environment or package assumptions recorded
- incomplete or speculative conclusions labeled
