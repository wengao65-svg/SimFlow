---
name: simflow-gpumd
description: Provide GPUMD- and NEP-specific guidance for GPUMD simulation files, NEP training, fine-tuning, and restart files, element ordering, model deployment, static validation, selected output parsing, and troubleshooting. Use when requests mention GPUMD, NEP, GPUMDkit, neptrain/NEPTrainKit, calorine, run.in, model.xyz, nep.in, train.xyz, test.xyz, nep.restart, nep.txt, loss.out, thermo.out, neighbor.out, or GPUMD transport outputs. Combine with simflow-mlp for cross-tool dataset, validation, active-learning, transferability, or readiness methodology.
---

# GPUMD And NEP Domain Skill

## Purpose

Provide GPUMD/NEP-specific semantics to any current Research Task Skills that
need them, without owning real execution, approval, workflow state, or
persistence.

## Use when

- The task involves GPUMD `run.in`, `model.xyz`, `thermo.out`, `neighbor.out`,
  transport output, or neighbor diagnostics.
- The task involves NEP `nep.in`, `train.xyz`, `test.xyz`, `nep.restart`,
  `nep.txt`, or `loss.out`.
- GPUMD/NEP-specific deployment, restart, or narrow output semantics are needed.

## Do not use when

- The task has no GPUMD/NEP-specific file, command, deployment, restart, or
  output semantics.
- The requested final property analysis is engine-independent; pair this Skill
  with analysis guidance rather than expanding its scope.

## Domain principles

- Distinguish GPUMD simulation, NEP training, fine-tuning, restart, and
  production deployment.
- Never default an unknown request to NVT, training, or another common task.
- Treat provider and community examples as guidance, not proof of readiness.
- Keep dataset semantics, element/type order, units, and model provenance
  explicit.
- Limit parsing claims to fields that the inspected output actually supports.
- Combine with `simflow-mlp` when NEP work also needs cross-tool dataset,
  validation, active-learning, or production-readiness methodology.

## Minimum checks

- Required input, structure, potential/model, dataset, and restart files exist.
- Element order and type mapping agree across structures, datasets, and models.
- Training/test splits, descriptor settings, cutoffs, loss weights, and restart
  intent are explicit for NEP work.
- GPUMD run commands, ensembles, timestep, temperature, sampling, and output
  cadence match the requested observable.
- Existing output tables are complete, numeric, and interpreted with known
  columns and units.
- Model deployment is not called production-ready without validation evidence.

## Common failure modes

- Confusing a NEP training restart with transfer learning or fine-tuning.
- Mixing datasets or models with different element order.
- Treating decreasing training loss as sufficient validation.
- Parsing a numeric table without verifying its GPUMD/NEP role.
- Claiming real execution or successful training from prepared inputs.

## Escalate uncertainty when

- Provider-specific training policy, element order, dataset provenance, or
  restart semantics are unclear.
- Real execution, GPU resources, remote access, or destructive replacement of a
  model is requested.
- Validation evidence is insufficient for production use.

## Completion criteria

- GPUMD/NEP-specific files and task intent are consistent.
- Parser limits, missing inputs, and readiness gaps are explicit.
- No real execution or production claim is inferred from setup evidence alone.

## Optional references

- `references/gpumd_official_sources.md`
- `references/gpumd_file_map.md`
- `references/gpumd_static_inspection.md`
- `references/gpumd_selected_output_parsing.md`
- `references/gpumd_nep_evidence.md`
- `references/gpumd_nep_community_methodology.md`
- `references/gpumd_task_checklists.md`
- `references/gpumd_troubleshooting.md`
- `references/gpumd_tools.md`
