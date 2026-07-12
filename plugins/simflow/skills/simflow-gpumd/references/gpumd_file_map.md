# GPUMD File Map

Map software-specific files to generic MLP evidence roles without changing the
shared helper-evidence schema:

| GPUMD/NEP artifact | Generic MLP evidence role |
| --- | --- |
| `train.xyz` / `test.xyz` | dataset evidence |
| `nep.in` | trainer configuration |
| `loss.out` | training metrics |
| `nep.restart` | checkpoint/restart lineage |
| `nep.txt` | model artifact |
| `run.in` / `model.xyz` | MD validation inputs |
| `thermo.out` | MD stability evidence |
| `neighbor.out` | runtime/structural diagnostic evidence |
| Thermal-transport or phonon outputs | target-property evidence |
| active-learning candidate structures | candidate-pool evidence |

Additional common files include `basis.in`, `kpoints.in`, `potential.in`,
potential/model files, `dump.xyz`, `movie.xyz`, `force.out`, `velocity.out`,
`msd.out`, `rdf.out`, `hac.out`, `kappa.out`, and `dos.out`, depending on the
task and requested commands.

`neighbor.out` generation and format are version- or toolchain-sensitive. Do
not assume it exists or apply a fixed diagnostic threshold without confirming
the current GPUMD version and producer.

Treat unknown GPUMD-family files as evidence artifacts with warnings rather than interpreting them by filename alone.
