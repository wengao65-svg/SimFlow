# MLP Scope And Toolchains

`simflow-mlp` covers evidence standards for machine-learning potentials across tools. It does not replace concrete engine helpers and does not execute workflows.

Common toolchain roles:

- Sampling: AIMD, classical MD, GPUMD, LAMMPS, ASE, custom scripts.
- Labeling: VASP, CP2K, other DFT engines, user-provided labels.
- Training: GPUMD/NEP, DeePMD, MACE, NequIP, Allegro, custom frameworks.
- Validation MD: GPUMD, LAMMPS, ASE, custom scripts.
- Analysis: Python, notebooks, NEPTrainKit, GPUMDkit, custom scripts.

Record actual tools, support levels, commands, versions, environment, and lineage without turning this into an executor DAG.
