# GPUMD Troubleshooting

Common evidence issues:

- Missing `run.in`, `model.xyz`, `nep.in`, `train.xyz`, or model files referenced by inputs.
- Output files are absent because the relevant command was not requested or the run did not complete.
- Table outputs have inconsistent columns, truncated rows, or mixed text/numeric content.
- NEP training evidence lacks dataset lineage, validation split, test metrics, or model hashes.
- Long MLP-MD evidence lacks smoke-test, anomaly, and production-readiness gate records.

Report what evidence is missing and which claim it blocks.
