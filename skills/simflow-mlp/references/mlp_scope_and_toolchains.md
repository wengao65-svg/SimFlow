# MLP Scope And Toolchains

`simflow-mlp` covers evidence standards for machine-learning potentials across tools. It does not replace concrete engine helpers and does not execute workflows.

Common toolchain roles:

- Sampling: AIMD, classical MD, GPUMD, LAMMPS, ASE, custom scripts.
- Labeling: VASP, CP2K, other DFT engines, user-provided labels.
- Training: GPUMD/NEP, DeePMD, MACE, NequIP, Allegro, custom frameworks.
- Validation MD: GPUMD, LAMMPS, ASE, custom scripts.
- Analysis: Python, notebooks, NEPTrainKit, GPUMDkit, custom scripts.

Record actual tools, support levels, commands, versions, environment, and lineage without turning this into an executor DAG.

## Provider boundary

The generic MLP layer records the scientific target, target configuration
domain, dataset and label provenance, training and validation evidence,
active-learning lineage, deployment evidence, and residual risk. It must
identify both the actual trainer and the downstream MD provider.

Provider-specific skills define how their software implements optimization,
loss scheduling, learning-rate scheduling, restart, fine-tuning, model export,
and runtime diagnostics. Map their files and outputs to generic MLP evidence
roles instead of importing their configuration syntax into this reference.

Active-learning iterations are outer dataset/label/retraining cycles. They are
not interchangeable with a trainer's internal scheduler, checkpoint restart,
fine-tuning mode, or optional stage transition.
