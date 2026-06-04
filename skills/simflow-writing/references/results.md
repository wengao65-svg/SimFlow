# Results

Use this guide to draft Results sections from processed data, rough analysis plots, and a figure storyboard. Do not wait for publication-quality figures, but do not draft Results before the main data trends are known.

## Correct Workflow

1. Finish core data processing enough to know the trends and uncertainties.
2. Build a figure storyboard: each figure answers one question.
3. Make rough analysis plots to test whether the story is supported.
4. Draft Results and figure captions together.
5. Use the draft to identify missing controls, error bars, labels, or extra analyses.
6. Polish publication-quality figures only after the claim-evidence chain is stable.

This prevents wasting time on beautiful figures that do not survive the story.

## What Results Must Do

Results must convert data into evidence. Each subsection should answer one scientific question and move the reader to the next question.

Every Results subsection should contain:

1. Question or purpose.
2. Simulation/data setup needed to understand the result.
3. Observation.
4. Quantification.
5. Baseline/control/reference.
6. Interpretation limited to what the data support.
7. Transition to the next result.

## Corpus Patterns

Method papers in the local corpus typically order Results as:

1. Framework/model overview.
2. Dataset construction and coverage.
3. Accuracy benchmark.
4. Transferability, sample efficiency, uncertainty, or ablation.
5. MD stability and property validation.
6. Downstream applications.

Examples include DPA-2 moving from LAM workflow to datasets/descriptor, zero-shot generalization, fine-tuning, distillation, and applications; CHGNet moving from architecture and MPtrj dataset to charge constraints and charge-informed applications; UNEP-v1 moving from architecture/training to accuracy, uncertainty, and alloy applications.

Physical-problem papers typically order Results as:

1. Simulation setup and validation.
2. Direct observation of the debated phenomenon.
3. Mechanistic descriptors.
4. Comparison with experiment/spectra/prior theory.
5. Condition dependence or prediction.

Examples include graphene wettability moving from models and water orientation to supported graphene, intercalated water, vSFG spectra, and thermodynamics; Ti3O5 moving from phase diagram to metastable phases, direct MD, phase growth, and transition pathway.

Reliability/statistics papers typically order Results as:

1. Estimator or fitting procedure.
2. Demonstration of error source.
3. Statistical model/variance relation.
4. Practical accessible-regime map.
5. Reanalysis or guidelines.

## Subsection Titles

Prefer claim-bearing titles over topic labels.

Weak:
> Model validation

Stronger:
> The potential remains stable across high-temperature liquid and crystalline regimes

Weak:
> Diffusion results

Stronger:
> Limited diffusion events dominate the uncertainty of AIMD diffusivities

For Nature-style papers, concise noun-phrase headings are acceptable, but the first sentence must still state the claim.

## Opening a Results Subsection

Use one of these forms:

Purpose-first:
> To test whether [method/model] can be used for [downstream task], we first evaluate [metric/property] on [test set/regime].

Question-first:
> We next ask whether [observed trend] reflects [mechanism] rather than [alternative].

Figure-first:
> Figure 2 compares [model/result] with [reference] across [conditions], establishing [takeaway].

Avoid:
> The results are shown in Fig. 2.

That sentence describes location, not meaning.

## Paragraph Formula

Use this formula for most Results paragraphs:

1. "We calculated/measured/simulated [quantity] using [minimal method/context]."
2. "The result shows [trend/contrast], with [number/range/uncertainty]."
3. "Compared with [DFT/AIMD/experiment/baseline], [agreement/deviation] indicates [validation or physical meaning]."
4. "This supports [claim] because [mechanism or logic]."

Do not include full Methods details unless the reader needs them to interpret the figure.

## Quantification Rules

State numbers when possible:

- model errors: MAE/RMSE for energy, force, stress, property
- trajectory scale: atoms, ps/ns, number of trajectories, number of seeds
- thermodynamic conditions: T, P, strain, electric field, composition
- property values: diffusivity, activation energy, thermal conductivity, transition temperature, barrier, spectra peak shift
- uncertainty: error bars definition, standard deviation, confidence interval, ensemble spread, block/bootstrap error

If a figure shows a trend but the text has no number, add the most important number.

## Method-Paper Results Order

Use this order unless the user's story requires a deliberate change:

1. Framework overview.
   Explain what is new in the architecture/workflow/training, using Fig. 1.

2. Dataset and coverage.
   Describe how the training/test data cover chemical and configurational space. Mention why this coverage is relevant to target applications.

3. Static accuracy.
   Report energy/force/stress errors by subset and against baselines. Do not stop here.

4. Transferability/sample efficiency.
   Show zero-shot/fine-tuning/out-of-domain performance, learning curves, ablations, or uncertainty-guided sampling gains.

5. MD stability and property validation.
   Demonstrate stable trajectories and property-level agreement: RDF, MSD, phonons, diffusion, thermal conductivity, phase transition, spectra, or mechanical response.

6. Enabled application.
   Show the simulation the method was built to enable: larger system, longer time, more complex chemistry, realistic condition, or new prediction.

## Physical-Problem Results Order

1. Establish trust.
   Validate the simulation method for the specific property, not just general force error.

2. Show the phenomenon.
   Present the direct trajectory/spectrum/phase/property observation.

3. Explain mechanism.
   Use order parameters, local environments, free energy, transition matrices, charge/spin, RDF, MSD, VDOS, spectra, or snapshots.

4. Rule out alternatives.
   Compare controls: substrate/no substrate, defect/no defect, mono/multilayer, functional, composition, temperature, pressure, or model variants.

5. Connect outward.
   Explain experiment, prior theory, design rule, or prediction.

## Reliability/Statistics Results Order

1. Define the estimator.
   State what is fitted or averaged and what region/window is valid.

2. Show the failure mode.
   Demonstrate how short trajectories, ballistic regimes, poor upper fitting bounds, finite events, or finite size affect the estimate.

3. Quantify uncertainty.
   Relate variance to events, total displacement, independent trajectories, ensemble spread, or block statistics.

4. Provide practical thresholds.
   Give usable criteria: minimum events, total MSD, trajectory length, accessible diffusivity, temperature range, or uncertainty target.

5. Apply to examples.
   Reanalyze representative systems and report uncertainty in final quantities.

## Transitions Between Figures

Each figure should motivate the next:

- Fig. 1 gives the workflow, so Fig. 2 must prove the data/model is valid.
- Fig. 2 proves accuracy, so Fig. 3 can ask whether it transfers.
- Fig. 3 proves transfer, so Fig. 4 can deploy MD.
- Fig. 4 reveals a phenomenon, so Fig. 5 explains mechanism.
- Fig. 5 explains mechanism, so Fig. 6 gives prediction or implication.

If two figures answer the same question, merge or demote one to Supplementary.

## Common Failures

- Results read like a Methods section.
- The text says "good agreement" without numbers.
- The first Results figure is already a complex application before validation.
- Model validation is separated from the property actually claimed.
- A single trajectory snapshot is treated as mechanism.
- Missing error bars for fitted trajectory-derived quantities.
- The discussion of limitations appears only after reviewers ask.

## Final Check

For every paragraph, write its claim in the margin. If the claim is "we plotted X", rewrite. The claim should be "X demonstrates Y under condition Z."
