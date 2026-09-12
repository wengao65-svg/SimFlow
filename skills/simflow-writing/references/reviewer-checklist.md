# Computational Simulation Manuscript Reviewer Checklist

Use for a requested review or final evidence check. This is an internal review
aid, not the default outline or vocabulary for drafting Results, Methods, or
Discussion. Apply only relevant questions. Return findings when review is
requested; otherwise address issues in the text and separate unresolved author
queries from manuscript prose.

## Claim Calibration

- Is the main claim stated in one sentence?
- Does the contribution concern physics, theory/method, data/resource, statistics,
  or a combination, with scale considered where relevant?
- Does every major claim have evidence, including derivation or qualitative
  observation where those are appropriate, rather than a mandatory figure?
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
- Are competing interpretations assessed, with unresolved alternatives retained
  rather than declared ruled out without discriminating evidence?

## Writing and Figures

- Does the first figure orient a reader who is not a method insider?
- Does each figure title/takeaway answer a scientific question?
- Are method details sufficient but not allowed to bury the story?
- Are limitations acknowledged in a way that strengthens credibility?
- Does the text explain scientific findings rather than announce passed checks?
- Are transitions justified by the evidence rather than invented for narrative flow?
- Are validation and limits placed where interpretation needs them, without a
  compulsory validation-first order or repetitive defensive disclaimers?
- Did revision preserve values, definitions, uncertainty, exclusions, and scope?
