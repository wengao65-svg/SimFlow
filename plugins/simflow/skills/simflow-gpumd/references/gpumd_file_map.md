# GPUMD File Map

Common GPUMD/NEP evidence roles:

- `run.in`: GPUMD run commands and output requests.
- `model.xyz`: GPUMD structure/model input.
- `basis.in`, `kpoints.in`, `potential.in`, and potential/model files: optional inputs depending on task.
- `nep.in`: NEP training configuration.
- `train.xyz`, `test.xyz`: NEP training and test datasets.
- `nep.txt`: NEP model artifact.
- `loss.out`: NEP training loss-style output when present.
- `thermo.out`: GPUMD thermodynamic time series when requested.
- `dump.xyz`, `movie.xyz`, `force.out`, `velocity.out`, `msd.out`, `rdf.out`, `hac.out`, `kappa.out`, `dos.out`: selected outputs depending on run commands.

Treat unknown GPUMD-family files as evidence artifacts with warnings rather than interpreting them by filename alone.
