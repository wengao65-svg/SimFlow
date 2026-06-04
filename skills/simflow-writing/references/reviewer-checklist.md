# Computational Simulation Manuscript Reviewer Checklist

Use before submission or when revising a draft.

## Claim Calibration

- Is the main claim stated in one sentence?
- Is the claim method, physics, scale, statistics, or hybrid?
- Does every major claim have a corresponding figure or quantitative result?
- Are universality, transferability, and accuracy claims limited to demonstrated regimes?

## DFT and Data

- Are functional, dispersion, Hubbard U, pseudopotentials, cutoffs, k-points, convergence criteria, and spin settings specified?
- Is the training/test split physically meaningful, not only random?
- Are structures from production regimes represented in validation?
- Are energies consistently referenced across compositions, cells, or charge states?

## MLP Validation

- Are energy, force, and stress/virial errors reported where relevant?
- Are errors broken down by phase, composition, temperature, pressure, defect, interface, or reaction class?
- Is there a baseline comparison?
- Is there an ablation for the new method ingredient?
- Is uncertainty or extrapolation detection reported when used?

## MD Reliability

- Are timestep, ensemble, thermostat/barostat, cell size, trajectory length, equilibration, and production windows specified?
- Are multiple seeds or independent trajectories used when stochastic behavior matters?
- Is energy conservation checked for NVE when appropriate?
- Are finite-size and finite-time effects discussed?
- Are rare events supported by statistics rather than a single trajectory?

## Physical Properties

- Are computed properties compared with DFT, experiment, or trusted literature where possible?
- Are uncertainty bars or confidence intervals provided for fitted quantities?
- Are order parameters or descriptors defined clearly?
- Are alternative mechanisms considered and ruled out?

## Writing and Figures

- Does the first figure orient a reader who is not a method insider?
- Does each figure title/takeaway answer a scientific question?
- Are method details sufficient but not allowed to bury the story?
- Are limitations acknowledged in a way that strengthens credibility?
