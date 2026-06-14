# GPUMD Static Inspection

Static inspection may check:

- Required file presence for an existing GPUMD directory: usually `run.in` and `model.xyz`.
- Required file presence for an existing NEP training directory: usually `nep.in`, `train.xyz`, and optional `test.xyz`.
- Referenced filenames in input files and whether they exist relative to the calculation directory.
- Obvious command categories such as ensemble, potential/model references, dump/output requests, and run-like commands.
- Risk warnings for missing predecessors, empty input files, absent model/dataset files, and ambiguous command semantics.

Do not infer that the input is scientifically valid, production-ready, or executable on the current machine.
