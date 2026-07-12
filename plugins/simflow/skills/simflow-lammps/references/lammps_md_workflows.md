# LAMMPS MD Workflows

LAMMPS workflows should be recorded by evidence and intent, not collapsed into
one generic "MD run".

## Common Routes

- `minimize`: geometry/force relaxation before dynamics or static evaluation.
- `equilibration`: temperature/pressure stabilization with explicit stop criteria.
- `production`: data collection after equilibration, with restart and dump strategy.
- `rerun`: post-processing existing trajectories under a specified potential.
- `deformation` or shock: `fix deform`, moving walls, impact, or boundary-driven dynamics.
- `transport`: MSD/VACF/Green-Kubo/nonequilibrium observables requiring long sampling.

## Smoke Versus Production

Smoke runs check syntax, package loading, model deployment, finite forces, and
basic stability over a short window. Production runs require separate evidence:
equilibration boundary, sampling length, statistical uncertainty, restart
policy, and approval for real execution.

## Required Workflow Notes

Record timestep, ensemble, thermostat/barostat damping, constraints, neighbor
settings, restart cadence, dump cadence, thermo cadence, and the reason these
choices are appropriate for the units and force field.

Unknown workflows should return candidate routes and missing evidence. Do not
default them to NVT, NVE, or any fixed helper template.
