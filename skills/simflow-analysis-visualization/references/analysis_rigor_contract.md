# Analysis Rigor Contract

Use this reference before a scientific analysis or comparison. It is a
lightweight reasoning contract, not a required file, runtime record, or workflow
stage. Scale the detail to the claim and keep it inline for ordinary work.

## Analysis Contract

State or infer, without inventing missing facts:

- scientific question: the decision or phenomenon the analysis addresses
- analysis object: runs, trajectories, structures, atoms, configurations,
  spectra, paths, models, or other evidence being summarized
- comparison object: baseline, condition, model, method, reference state, or no
  comparison when the task is descriptive
- window and transformation: equilibration/production range, selection, stride,
  filtering, binning, smoothing, alignment, fit range, normalization, or
  reference-zero operation
- uncertainty approach: independent seeds, blocks, bootstrap unit, model-based
  interval, sensitivity range, or an explicit reason no defensible estimate is
  available
- claim level: diagnostic, descriptive, comparative, quantitative estimate,
  mechanistic interpretation, or production/publication claim

If these items are unresolved, keep the result exploratory or conditional. Do
not silently upgrade an exploratory choice into a final analysis convention.

## Statistical Unit And Dependence

Define the unit that could have varied independently under the data-generating
process. Then map lower-level observations onto it.

- Independent seeds or separately initialized trajectories may be replicate
  units when they do not share continuation history or reused fluctuations.
- Restart segments from one trajectory are normally one dependent trajectory,
  not new replicates.
- Frames from one trajectory, atoms within one configuration, spatial bins,
  repeated evaluations of one structure, and overlapping time origins are
  usually correlated subsamples.
- Configurations drawn from one correlated trajectory are not automatically
  independent; justify thinning, blocking, correlation-time treatment, or a
  hierarchical method.
- Multiple time origins improve an estimator but do not create that many
  independent trajectories. Bootstrap or resample at the level that preserves
  the dependence structure.
- Report both the observation count and independent-unit count when they differ.
  Do not use frame count as `n` for between-run inference.

When independence cannot be defended, prefer descriptive summaries, block
statistics, hierarchical or repeated-measures reasoning, or wider claim limits.

## Cross-Run And Cross-Model Comparability

Before combining, ranking, subtracting, fitting across, or placing results on a
shared axis, check:

- physical quantity and unit conversion
- per-atom, per-formula-unit, per-area, per-volume, per-mode, or total
  normalization
- energy/Fermi/reference zero and baseline subtraction
- atom/species/region/mode selections and ordering
- ensemble, temperature, pressure, composition, cell, system size, timestep,
  sampling interval, and trajectory length when relevant
- equilibration cut, production window, stride, correlation/integration length,
  fit range, broadening, smoothing, binning, and interpolation
- method settings that alter the observable, such as functional, basis,
  pseudopotential, k/q mesh, spin/SOC, MLP identity, or correction scheme
- convergence, failed-run, missing-frame, and censoring status

Reconcile a mismatch by a justified transformation and preserve the original
values. If it cannot be reconciled, compare only conditionally, stratify the
results, or state that the quantities are not directly comparable. A common
plotting scale does not make unlike quantities comparable.

## Sensitivity Analysis

Identify analyst choices that could plausibly change the sign, ordering,
magnitude, plateau, peak, fitted coefficient, uncertainty, or claim. Typical
choices include equilibration and production windows, cutoff radius, bin width,
smoothing bandwidth, time-origin strategy, block size, fit range, integration
limit, reference zero, broadening, normalization, exclusions, and interpolation.

- Test a small set of scientifically defensible alternatives rather than an
  exhaustive grid chosen to find a preferred result.
- Keep invariant processing choices aligned across compared groups unless the
  difference is itself justified and disclosed.
- Report the default choice, alternatives tested, and whether the claim is
  stable, magnitude-sensitive, sign-sensitive, or unresolved.
- If a reasonable alternative changes the conclusion, make that dependence part
  of the result and weaken or split the claim. Do not hide it in plotting code.
- Absence of a sensitivity analysis is acceptable only when the choice is fixed
  by the method or immaterial to the intended claim; state that reasoning when
  it is not obvious.

## Unexpected-Result Diagnostic Ladder

Do not begin with a novel physical explanation. Move through the ladder and
retain the first unresolved level as a limitation:

1. Parsing and identity: wrong file, column, species/type map, frame index,
   duplicate/missing records, stale derived data, or parser fallback.
2. Units and conventions: unit conversion, sign, dimensionality, normalization,
   wrapped coordinates, energy/Fermi/reference zero, or label ordering.
3. Calculation health: incomplete termination, unconverged SCF/forces, failed
   images/frames, thermostat/barostat pathology, restart discontinuity, or
   corrupted output.
4. Analysis artifact: window, cutoff, bin, smoothing, interpolation, fit range,
   integration tail, alignment, selection, or visualization scale.
5. Sampling: equilibration, trajectory length, autocorrelation, rare events,
   finite size, seed variability, or insufficient independent units.
6. Model or method validity: extrapolative MLP states, unsuitable functional or
   force field, missing physics, inconsistent predecessor calculations, or
   known method limits.
7. Physical interpretation: only after earlier levels are checked should the
   result motivate a physical hypothesis, preferably with a discriminating
   follow-up diagnostic.

An unresolved diagnostic is not evidence for the most interesting explanation.

## Figure To Data To Claim Trace

For each claim-bearing figure or table, be able to answer in both directions:

- Figure to data: which source and derived data produced each panel, through
  which selections, transformations, statistics, and plotting parameters?
- Data to claim: which exact claim does the displayed evidence support, at what
  claim level and under which uncertainty and sensitivity limits?
- Claim to figure: does every substantive use of the figure in a caption,
  summary, or handoff stay within what the data show?
- Non-claims: what does the figure not establish, such as causality, mechanism,
  convergence, transferability, direct comparability, or generality beyond the
  sampled conditions?

Decompose compound captions or claims. If one part is unsupported, do not let a
supported part make the whole statement pass. A figure may be visually correct
and still fail as evidence because its transformation is untraceable or its
claim is overstated.

## Delivery Scaling

- Exploratory: preserve enough parameters and provenance to reproduce the
  analysis; no mandatory visual-QA loop or figure manifest.
- Review/draft: expose statistical units, comparability, uncertainty,
  sensitivity, and claim limits where they affect interpretation.
- Final/publication/handoff: add the optional visual QA and figure contract in
  `figure_contract_and_visual_qa.md`, then verify figure-data-claim consistency.

This contract guides analysis quality only. It does not create SimFlow state,
approve execution, or decide that a calculation is scientifically complete.
