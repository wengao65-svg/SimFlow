---
name: simflow-mlp
description: Provide general machine-learning-potential domain assistance for dataset and labeling provenance, training evidence, validation metrics, active-learning loops, production MLP-MD readiness, evidence handoff, and artifact recording across GPUMD/NEP, DeePMD, MACE, NequIP, Allegro, LAMMPS, ASE, Python, VASP, CP2K, and custom MLP workflows.
---

# SimFlow MLP

`simflow-mlp` is a general domain assistant for machine-learning-potential evidence. It is not a central workflow executor, is not tied to one package, and does not make any MLP software a central executor. Use concrete engine helpers, such as `simflow-gpumd`, only for tool-specific file evidence.

## Trigger conditions

- User mentions MLP, machine-learning potential, interatomic potential training, active learning, dataset split, DFT labels, force/energy/stress metrics, extrapolation, anomaly detection, model validation, foundation potential, or production MLP-MD readiness.
- A proposal, computation, analysis_visualization, writing, or handoff task needs cross-tool MLP evidence standards.
- User asks to audit dataset lineage, training evidence, validation sufficiency, active-learning rounds, or long MLP-MD readiness.

## Input conditions

- User-provided datasets, label manifests, training logs, model artifacts, validation reports, metrics tables, active-learning round notes, long-MD smoke evidence, anomaly reports, artifact ids, or checkpoints.
- Optional software/toolchain context such as GPUMD/NEP, DeePMD, MACE, NequIP, Allegro, LAMMPS, ASE, Python, VASP, CP2K, or custom scripts.
- Unknown tools or unlisted MLP frameworks should be recorded as provenance with explicit uncertainty rather than forced into a supported helper path.
- For ambiguous setup, clarify MLP family, target chemistry/configuration domain, reference-label source, dataset split, validation criteria, active-learning loop state, and whether any real execution is requested.

## Output artifacts

- Optional dataset manifest, labeling provenance report, training-run manifest, validation summary, metric summary, active-learning round manifest, production-readiness review, helper-run manifest, or handoff package.
- Artifact metadata should record recipe `mlp_md` when applicable, iteration id, evidence role, toolchain, actual tool used, support level, source files, hashes, assumptions, thresholds, parent artifacts, and lineage.
- Scientific claims must link to validation evidence and limitations; incomplete evidence should be recorded as missing or degraded, not passed.

## Status write rules

- Read `.simflow/state/` before acting when workflow state is relevant, and resolve explicit `project_root` before writing `.simflow/` reports, artifacts, checkpoints, or helper-run manifests.
- Keep MLP activities as recipe/helper metadata inside existing stages such as `proposal`, `computation`, `analysis_visualization`, and `writing`.
- Do not change tool-level support for GPUMD, NEP, DeePMD, MACE, NequIP, Allegro, or custom tools unless the shared toolchain contract is explicitly updated.
- Do not write under `.omx/`; it belongs to the host session, not SimFlow workflow state.

## Working procedure

1. Classify the request as dataset/labeling audit, training evidence review, validation metrics summary, active-learning readiness, production MLP-MD readiness, writing, or handoff.
2. Load `references/mlp_scope_and_toolchains.md` for boundaries, `references/mlp_dataset_and_labeling.md` for data provenance, `references/mlp_training_validation.md` for training and metric checks, and `references/mlp_active_learning_readiness.md` for loop/readiness checks as needed.
3. Inspect local evidence before drawing conclusions. Report missing dataset lineage, label convergence, split definitions, failed-label exclusions, or validation thresholds.
4. Use optional helper scripts for evidence manifests and summaries only. Real training, inference, MD, remote execution, or HPC submission requires generic computation evidence and approval gates.
5. Register generated evidence reports, figures, or handoff summaries as artifacts with metadata and lineage when writing SimFlow state.

## Reference map

- `references/mlp_scope_and_toolchains.md`: Cross-tool scope and helper boundaries.
- `references/mlp_dataset_and_labeling.md`: Dataset, labels, splits, and provenance checks.
- `references/mlp_training_validation.md`: Training evidence, metrics, validation regimes, and limitations.
- `references/mlp_active_learning_readiness.md`: Active-learning and production MLP-MD readiness checks.
- `references/mlp_evidence_handoff.md`: Handoff package expectations.
- `references/mlp_artifact_schemas.md`: Lightweight JSON evidence contracts and status semantics.
- `references/mlp_task_checklists.md`: Task-oriented checklists.
- `references/mlp_troubleshooting.md`: Missing or conflicting evidence diagnosis.

## Optional helper scripts

- `scripts/build_mlp_dataset_manifest.py`: Build a dataset manifest from existing dataset files and metadata.
- `scripts/validate_mlp_evidence.py`: Check whether required MLP evidence roles are present for review or readiness.
- `scripts/summarize_mlp_metrics.py`: Summarize user-provided metric files without declaring production readiness by default.
- `scripts/prepare_mlp_handoff.py`: Package MLP evidence roles, limitations, and next actions into handoff JSON.

These helpers are optional domain tools, not the only valid MLP workflow, parser, model family, report structure, or analysis path.

## Checkpoint rules

- Create a checkpoint only when MLP evidence is ready for review, active-learning decision, production-readiness gate, or handoff.
- Create failure checkpoints for true helper failures such as conflicting dataset lineage, unreadable evidence, unavailable proprietary data, validation failure, or blocked approval gates.
- For unsupported training, inference, MD, input-generation, or submit requests, return a `capability_warning` and keep workflow state waiting; do not record a completed or failed checkpoint solely for the unsupported capability.

## Prohibited actions

- Do not treat `simflow-mlp` as a training, inference, MD, or active-learning executor.
- Do not require one MLP package, parser, descriptor family, model architecture, report filename, or metric threshold as the only valid path.
- Do not run training, inference, local MD, remote jobs, or HPC jobs from this skill without the relevant approval gate.
- Do not fabricate datasets, labels, metrics, model quality, convergence, extrapolation status, production readiness, figures, citations, or completed calculations.
- Do not record unfinished, failed, or missing-validation work as completed production-ready evidence.

## Manual confirmation scenarios

- Real local, remote, or HPC training/MD/inference execution is requested.
- Dataset ownership, proprietary model files, credentials, licensed files, or private paths may be exposed.
- Validation thresholds, active-learning stopping criteria, or production MLP-MD readiness affect a scientific conclusion.
- Existing evidence would be overwritten, filtered, split, or interpreted in a way that changes scientific meaning.
