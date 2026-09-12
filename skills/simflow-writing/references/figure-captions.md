# Figure Captions

Use this guide to write computational simulation figure captions. Supply what a
reader needs to interpret the displayed evidence. Length follows interpretive
need: detailed reference definitions can be essential, while routine settings
can remain in Methods. Captions are not miniature audit reports.

## Corpus Patterns

Nature-family captions usually follow:

> Fig. X | Takeaway-style title. a, Panel explanation. b, Panel explanation. Error bars/conditions/data sources...

The title after the vertical bar often states the figure's role, such as model architecture, benchmark, phase diagram, mechanism, or comparison.

PR/arXiv captions usually follow:

> FIG. X. Descriptive title. (a) Panel explanation. (b) Panel explanation...

They are often more technical and less headline-like, but still need enough conditions and definitions for standalone reading.

## Select Relevant Information

Check which of these details the displayed figure requires; they are not seven
mandatory clauses for every caption:

1. Takeaway or role of the figure.
2. What each panel shows.
3. Essential simulation conditions.
4. Model/reference/baseline used.
5. Definitions of symbols, colors, labels, and fitted lines.
6. Error-bar/statistics definition.
7. Units and normalization when not obvious from axes.

A descriptive or takeaway-style opening can orient the reader. Do not force a
mechanistic conclusion into a diagram title or repeat the full Results argument.
Define any displayed error bars, nonstandard symbols, and non-obvious normalization.
Do not invent uncertainty estimates, baselines, or statistical replication when absent.

## Caption Title Types

Workflow:
> Fig. 1 | Active-learning workflow for constructing a transferable MLP.

Dataset:
> Fig. 2 | Training configurations cover the relevant thermodynamic and structural regimes.

Validation:
> Fig. 3 | The MLP reproduces DFT forces and property-level benchmarks across test regimes.

Mechanism:
> Fig. 4 | Water intercalation reverses the apparent spectral signature of supported graphene.

Statistics:
> Fig. 5 | Diffusivity uncertainty is controlled by the number of sampled hopping events.

Prediction:
> Fig. 6 | Large-scale MLP-MD predicts a temperature-dependent phase-growth mechanism.

## Panel-by-Panel Pattern

Follow the actual panel order. One possible arrangement is:

1. `a,` Define the system, workflow, or primary quantity.
2. `b, c,` Show comparisons or trends.
3. Later panels show mechanism, controls, or implications.
4. End with shared conditions or statistical definitions if they apply to all panels.

Example skeleton:

> Fig. X | [Takeaway]. a, [System/workflow/structure] showing [key definitions]. b, [Quantity] computed using [method] under [T/P/composition], compared with [reference]. c, [Mechanistic descriptor] demonstrating [trend]. Error bars denote [definition] from [number] independent trajectories/seeds.

## Computational Information to Include

Include only the details required to interpret the figure:

- DFT reference: functional level or "DFT reference" if detailed settings are in Methods.
- MLP type if comparing models.
- Ensemble and thermodynamic conditions when the plotted quantity depends on them.
- Cell size or atom count when finite-size effects matter.
- Trajectory length and number of independent runs when statistics matter.
- Definition of derived quantities: MSD fitting window, activation energy fit, thermal conductivity estimator, order parameter, coordination criterion, spectra normalization.
- Uncertainty definition: standard deviation, standard error, confidence interval, ensemble spread, bootstrap, block average, or fit uncertainty.

Do not include full pseudopotential, cutoff, k-point, thermostat, and training hyperparameters unless the figure specifically compares those settings.

## Captions for Common Figure Roles

### Method/Workflow Figure

Define the applicable elements shown:

- inputs and outputs
- training/active-learning/fine-tuning/distillation loop
- reference data source
- where uncertainty or selection enters
- what is new relative to standard workflows

Explain the depicted method; a workflow need not be Fig. 1 or summarize the
whole paper. Theory or algorithms without training loops need no such loop.

### Dataset/Coverage Figure

Define the applicable elements shown:

- what each point/configuration represents
- descriptor used for PCA/UMAP/SOAP/kPCA if shown
- grouping by phase, composition, temperature, pressure, defect, interface, or trajectory source
- train/test split or reference set

State the takeaway:
Describe the observed overlap or separation without treating a low-dimensional
projection alone as proof of interpolation, extrapolation, or adequate coverage.

### Accuracy/Benchmark Figure

Define the applicable elements shown:

- reference method
- train/test or validation set
- metric and units
- baseline model
- whether errors are per atom, per structure, per component, or per force component

If using parity plots, mention the diagonal and error statistics. If using learning curves, mention training-set size and repeated runs.

### MD/Property Figure

Define the applicable elements shown:

- ensemble, temperature/pressure, trajectory length, and system size if relevant
- property estimator
- fitting window or convergence procedure
- uncertainty source
- comparison target

For diffusion error bars, define whether they come from trajectories, fitting,
or Arrhenius regression. Missing uncertainty is an author query or a claim
limitation, not permission to invent error bars.

### Mechanism Figure

Define the applicable elements shown:

- order parameter or descriptor
- state classification rule
- representative snapshots and color legend
- transition/pathway arrows
- whether snapshots are representative or selected

Avoid using snapshots alone as proof. Pair them with quantitative descriptors.

## Reference and Scope Differences

If panels use different reference levels, sampled populations, or measured versus
extrapolated timings, state that distinction where the comparison is read. The
AI2BMD corpus example distinguishes full and fragmented DFT references by system
size; this is a reason for a detailed caption, not expendable Methods clutter.
See `narrative-examples.md` for the source filename. Likewise, retain exclusions
or coordinate definitions that change what a free-energy panel represents.

## Caption Writing Rules

- Use present tense for what the figure shows.
- Use past tense only for how data were generated if needed.
- Keep panel descriptions parallel.
- Do not repeat the same method phrase in every panel; use a shared final sentence.
- Explain all nonstandard abbreviations in the caption or figure.
- State if lines are guides to the eye, fits, model predictions, or references.
- If a figure uses color to encode categories, define the categories in the caption.

## Common Failures

- Caption says only "Results of X" and does not state the takeaway.
- Error bars appear but are not defined.
- Axes use derived quantities whose definitions are absent.
- Snapshots have colors or labels that are not explained.
- Caption includes too many Methods details but omits the comparison reference.
- Panel order in caption does not match visual reading order.

## Final Check

A reader should be able to answer the applicable questions from the caption:

- What is being compared?
- Under what conditions?
- Against what reference?
- What do the colors/symbols/lines mean?
- What is the uncertainty?
- What conclusion should I take from the figure?
