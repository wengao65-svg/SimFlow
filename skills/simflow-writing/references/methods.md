# Methods

Use this guide to draft or audit Methods sections for computational materials/physics manuscripts. The patterns are distilled from local Nature, Nature Communications, Nature Machine Intelligence, npj Computational Materials, PRB, and arXiv papers involving DFT, AIMD, MD, MLP, active learning, metadynamics, transport, spectra, phase diagrams, and uncertainty analysis.

## Why Methods Deserves Its Own Reference

Yes: include `methods.md` as a separate reference. In computational simulation papers, Methods is not just a place for technical leftovers. It defines:

1. Reproducibility: another group can rerun or audit the work.
2. Validity domain: readers know where the model/simulation is trustworthy.
3. Error sources: DFT functional, finite size, trajectory length, sampling, and MLP extrapolation are exposed.
4. Reviewer defense: most computational-paper objections are Methods objections.
5. Separation of story and protocol: Results can stay readable because Methods carries procedural detail.

## Corpus Patterns

Nature-family papers often place a compact Methods section after Discussion. They use named subsections such as `Model training details`, `Molecular dynamics simulations`, `Reference data`, `Active learning`, `vSFG spectra simulations`, `Free energy calculations`, plus `Data availability` and `Code availability`.

PR/PRB/arXiv papers often place `Computational Methods` or `Models and Methods` before Results. They commonly use numbered sections and lettered subsections, for example `II. Computational Methods`, `A. Atomistic models`, `B. Potential model`, `C. Tight-binding model`, `D. Thermal conductivity method`.

npj reliability/statistics papers use Methods to define estimators, simulation settings, and analysis equations, but the practical procedure may also appear in Results/Discussion because the method itself is the contribution.

## Methods Versus Results

Put in Results:

- why a calculation was performed
- what the figure shows
- key numerical outcome
- interpretation and comparison

Put in Methods:

- exact software and versions when important
- DFT functional, dispersion, U, pseudopotential, cutoff, k-points, convergence
- dataset construction, filtering, labeling, split, and data counts
- MLP architecture, descriptors, loss, weights, hyperparameters, training hardware when relevant
- active-learning thresholds and selection criteria
- ensemble, timestep, thermostat/barostat, equilibration/production length, cell size
- property estimators, fitting windows, uncertainty definitions
- data/code availability

If a detail affects whether a plotted result is believable, mention a short version in Results and full version in Methods.

## Recommended Section Order

Use only the subsections relevant to the paper:

1. `First-principles calculations` or `Electronic-structure calculations`
2. `Reference data and dataset construction`
3. `Machine-learning potential training`
4. `Active learning and uncertainty/extrapolation control`
5. `Molecular dynamics simulations`
6. `Enhanced sampling/free-energy calculations`
7. `Property calculations and analysis`
8. `Statistical uncertainty and convergence`
9. `Data availability`
10. `Code availability`

For PR-style manuscripts, these may become `II.A`, `II.B`, etc. For Nature-style manuscripts, use concise subsection headings after Discussion.

## First-Principles Calculations

Must include:

- code/package
- exchange-correlation functional
- dispersion correction
- Hubbard U or spin settings if used
- pseudopotential/PAW/basis type
- plane-wave cutoff or basis details
- k-point mesh or gamma-only choice
- electronic convergence criteria
- ionic relaxation criteria
- supercell size and boundary conditions when relevant
- finite-temperature electronic smearing if relevant

Example structure:

> First-principles calculations were performed using [code]. Exchange-correlation effects were treated with [functional] and [dispersion/U/spin setting]. The [PAW/pseudopotential/basis] approach was used with [cutoff] and [k-point mesh]. Structures were relaxed until [force/stress criteria]. These settings were used to generate [energies/forces/stresses/charges/magnetic moments] for [dataset/task].

Do not simply say "DFT calculations were performed using VASP." That is not reproducible.

## Reference Data and Dataset Construction

Use this subsection when building or validating MLPs, active-learning datasets, databases, or benchmark sets.

Must include:

- source of initial structures
- structure generation: perturbation, AIMD, random search, defects, surfaces, interfaces, compositions, temperatures, pressures
- labeling method: DFT settings and labels used
- filtering/removal criteria: failed convergence, duplicates, energy outliers, deprecated tasks, inconsistent settings
- train/validation/test split strategy
- data counts: structures, atoms, elements, compositions, phases, trajectories
- whether test sets are random, physically separated, out-of-domain, or downstream

Write the split logic explicitly. A random split tests interpolation; a physically separated split tests transfer.

Example structure:

> The initial dataset contained [sources]. To cover [target regimes], we generated [configuration classes] over [T/P/composition]. Structures with [failure/outlier criteria] were removed. The final dataset contained [N] structures and [M] atoms. We used [split strategy], reserving [test set] to evaluate [interpolation/transfer/downstream stability].

## Machine-Learning Potential Training

Must include:

- model type and implementation
- descriptors/architecture and cutoffs
- predicted quantities: energy, forces, stress/virial, charges, magnetic moments, dipoles, etc.
- loss function components and weights
- optimizer, learning rate, batch size, epochs/steps
- initialization/pretraining/fine-tuning/distillation details
- ensemble model count if uncertainty is used
- units of reported errors
- hardware only if it supports cost/speed claims

For method papers, Methods can include equations. For physical papers, keep architecture details shorter and move heavy equations to Supplementary unless model design is central.

Example structure:

> The potential was trained to reproduce DFT energies, forces, and stresses by minimizing a weighted loss [define or cite]. The energy, force, and stress weights were [values]. The cutoff radius was [value]. Training used [optimizer] with [learning rate/batch/epochs]. Model accuracy was evaluated on [test sets] using [metrics].

## Active Learning and Extrapolation Control

Must include:

- initial model or dataset
- exploration simulations and conditions
- uncertainty/extrapolation metric
- selection threshold
- labeling procedure for selected structures
- stopping criterion
- number of iterations and final dataset size

Corpus examples use Bayesian error, committee disagreement, extrapolation grade, D-optimality, or teacher-student discrepancy. The exact metric matters because it defines the trust boundary.

Example structure:

> During active learning, MD simulations were performed under [conditions]. Configurations were selected for DFT labeling when [uncertainty metric] exceeded [threshold]. Selected structures were added to the training set and the potential was retrained. The loop was stopped when [criterion], yielding [final dataset].

## Molecular Dynamics Simulations

Must include:

- code/package
- potential/model used
- ensemble
- temperature and pressure control method
- thermostat/barostat relaxation times
- timestep
- equilibration and production lengths
- system size, atom count, cell dimensions, boundary conditions
- fixed atoms/constraints if any
- number of independent trajectories/seeds
- saved-frame interval if used for spectra/statistics

Example structure:

> MD simulations were performed using [code] with [potential]. Each system was equilibrated for [time] in [ensemble] at [T/P] using [thermostat/barostat], followed by [time] production in [ensemble]. A timestep of [dt] was used. The simulation cell contained [atoms/cell dimensions], with [boundary conditions/constraints]. Unless otherwise stated, reported averages were obtained from [number] independent trajectories.

For trajectory-derived quantities, do not omit trajectory length and number of seeds.

## Enhanced Sampling and Free Energy

Use for metadynamics, umbrella sampling, NEB, thermodynamic integration, 2PT entropy, phase diagrams, or rare-event studies.

Must include:

- collective variables or reaction coordinates
- bias type and parameters
- Gaussian height/width/deposition interval/bias factor for metadynamics
- simulation length and convergence criterion
- reweighting method
- NEB image count, force convergence, and endpoint preparation if relevant
- entropy/free-energy model and assumptions

Example structure:

> Well-tempered metadynamics was performed using [code/plugin]. The collective variable was [definition], chosen because it distinguishes [states]. Gaussians of width [value] and initial height [value] were deposited every [time] with bias factor [value]. Free energies were reconstructed using [method] after [simulation length], and convergence was assessed by [criterion].

## Property Calculations and Analysis

Write a separate subsection for each major property when the estimator is nontrivial.

Diffusion:

- MSD definition
- fitting window
- dimensionality factor
- temperature points
- Arrhenius fit and uncertainty
- finite-size/time checks if used

Thermal conductivity:

- Green-Kubo/HNEMD/NEMD method
- heat current definition
- driving force or correlation time
- quantum correction if used
- convergence and independent runs

Electronic/quantum transport:

- Hamiltonian model
- disorder/phonon treatment
- transport formalism
- system size and boundary conditions
- energy grid, correlation time, averaging

Spectra:

- dipole/polarizability model
- correlation function
- sampling length
- windowing/broadening/normalization
- frequency correction if used

Phase transitions:

- order parameter
- phase classification rule
- transition criterion
- hysteresis/finite-size checks if relevant

## Statistical Uncertainty and Convergence

Must include when reporting fitted or trajectory-derived quantities:

- what the error bars represent
- number of independent trajectories or blocks
- fitting uncertainty versus sampling uncertainty
- convergence checks with trajectory length, cell size, or model ensemble
- propagation to activation energies or extrapolated properties

Do not use "error bars denote standard deviation" without saying standard deviation of what: trajectories, blocks, model ensemble, fit residuals, or experimental spread.

For AIMD/MD diffusivity, fitting quality alone does not quantify statistical variance. Relate uncertainty to event count, total displacement, independent trajectories, or block analysis.

## Data and Code Availability

Nature-family papers normally require explicit Data availability and Code availability sections.

Include:

- source data for main figures
- training/test datasets
- trained potential files
- initial/final structures
- MD input files and trajectory logs when feasible
- analysis scripts or notebooks
- code repositories, versions, licenses, DOIs

If data are available on request only, explain what is included and why public deposition is not possible.

## Nature Versus PR Placement

Nature/NatCommun/npj:

- Put readable story in Results.
- Put technical protocols after Discussion in Methods.
- Use Data/Code availability sections.
- Move long derivations and hyperparameter tables to Supplementary.

PR/PRB/arXiv:

- Put `Computational Methods` or `Models and Methods` before Results.
- Equations and derivations can appear in the main Methods.
- Results and Discussion may be combined.
- Data availability often appears near the end.

## Common Reviewer Objections Methods Should Prevent

- DFT settings are insufficient to reproduce labels.
- Training/test split leaks similar structures.
- MLP was validated only by force MAE, not production-regime properties.
- Active-learning stopping criterion is unclear.
- MD trajectory is too short or lacks independent seeds.
- Error bars are undefined or represent only fitting residuals.
- Enhanced-sampling collective variable is not justified.
- Data/code availability does not include trained potentials or inputs.

## Final Methods Checklist

- Can another group reproduce the reference data?
- Can another group train or load the potential?
- Can another group rerun the production MD?
- Can another group recompute each plotted property?
- Are uncertainty bars traceable to a stated procedure?
- Are limits of the model and simulation protocol visible?

If the answer to any item is no, Methods needs more detail or the claim needs narrowing.
