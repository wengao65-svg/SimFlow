# Abstracts

Use this guide to draft or revise abstracts for computational materials/physics papers. The patterns are distilled from the local Nature/NatCommun/NatMachIntell/npj/PR corpus.

## What the Abstract Must Do

The abstract is not a miniature Methods section. It is a compressed argument:

1. Why the problem matters.
2. What blocks current understanding or simulation.
3. What this work introduces or shows.
4. What evidence proves it.
5. What new capability, mechanism, prediction, or reliability criterion follows.

If any of these five functions is missing, the abstract will feel generic.

## Corpus Patterns

Nature-family papers usually use one dense paragraph. They open with a field-level bottleneck, move quickly to "Here we...", include 1-3 quantitative results, and end with enabled capability or physical implication.

PR/arXiv-style papers often use an explicit `Abstract` heading and tolerate more technical detail. They still need the same argument, but the last sentence can be a more direct statement of the computed result or method scope.

Method papers in the corpus, such as DPA-1, DPA-2, CHGNet, GNoME, UNEP-v1, and the polarizable long-range foundation MLP, make the bottleneck concrete: data generation cost, model generation bottleneck, missing electronic/charge/long-range degrees of freedom, or lack of general-purpose transfer.

Physical-problem papers, such as graphene wettability, TiO2-water dissociation, Ti3O5 phase transformation, and GaN/BAs thermal management, open with a disputed or technologically important phenomenon, then present simulation as the route to mechanism.

Reliability/statistics papers, such as the AIMD diffusivity variance paper, begin from a widely used simulation practice and identify an underreported source of error.

## Before Drafting, Collect

- Manuscript type: method, physical-problem, scale-breakthrough, reliability/statistics, or hybrid.
- Main claim in one sentence.
- Exact system/material/process.
- Simulation stack: DFT/AIMD/MD/MLP/active learning/foundation model/etc.
- Best quantitative evidence: error metrics, data size, time/length scale, speedup, uncertainty, agreement with DFT/experiment, or property values.
- Main enabled result: mechanism, phase diagram, diffusivity, thermal transport, spectra, device insight, workflow, or reliability criterion.
- Limits that must constrain the claim if the result is narrow.

## Six-Sentence Abstract Skeleton

Sentence 1: Field pressure.
Name the scientific or technological area and the quantity/process that matters.

Sentence 2: Bottleneck.
State exactly why current experiment, DFT/AIMD, empirical MD, or existing MLPs cannot answer the problem.

Sentence 3: Contribution.
Use "Here we..." or equivalent. Name the method or discovery and attach it to the bottleneck, not to a software label alone.

Sentence 4: Evidence.
Report the strongest validation or benchmark with numbers where possible.

Sentence 5: Main result.
State the physical mechanism, new simulation regime, data-efficiency gain, prediction, or uncertainty criterion.

Sentence 6: Implication.
Explain what the field can now do, reinterpret, design, or report more reliably.

For shorter abstracts, merge Sentences 1-2 and 5-6. Do not remove the contribution or evidence sentence.

## Type-Specific Openings

Method:
> Atomistic simulations require accurate potential energy surfaces, but constructing reliable machine-learned potentials for [system/regime] remains limited by [data cost/transferability/physics missing].

Physical problem:
> [Material/interface/process] is central to [application/phenomenon], yet the microscopic origin of [debate/observation] remains unresolved because [experimental/computational limitation].

Scale breakthrough:
> Understanding [phenomenon] requires atomistic simulations over [length/time/condition], beyond the reach of conventional AIMD and unreliable for empirical force fields.

Reliability/statistics:
> [Computed quantity] is widely extracted from AIMD/MD trajectories, but its statistical uncertainty is often underestimated because [limited events/short trajectories/finite-size effects].

## Contribution Sentences

Weak:
> In this work, we use molecular dynamics to study X.

Stronger:
> Here we combine [validated MLP/DFT/AIMD/workflow] with [sampling/analysis] to determine [specific mechanism/property] under [conditions].

Method:
> Here we introduce [method/model], which [new ingredient] to enable [simulation capability] with [accuracy/efficiency/transfer].

Physical:
> Here we show that [observed phenomenon] originates from [mechanism], rather than [alternative explanation].

Reliability:
> Here we establish [estimator/protocol/criterion] that links [observed trajectory statistic] to [uncertainty in property].

## Evidence Sentence Rules

Use at least one specific number when the data exist:

- model errors: energy, force, stress, property error
- data size: configurations, elements, systems, temperatures, pressures
- scale: atoms, ns, trajectories, events
- speed: relative cost or time-to-solution
- agreement: DFT, AIMD, experiment, spectra, phase transition temperature, diffusivity, thermal conductivity
- uncertainty: confidence interval, standard deviation, RSD, seed-to-seed spread

Avoid:

- "excellent agreement" without reference or number
- "large-scale" without atom count or time scale
- "high accuracy" without specifying energy/force/property accuracy
- "universal" unless the chemical/configurational domain is actually demonstrated

## Ending Sentences

The final sentence should not merely repeat "this method is useful." It should name the new scientific or practical capability.

Method ending:
> These results establish [method] as a data-efficient route for [class of simulations] and define a validation path for deployment in [domain].

Physical ending:
> The findings provide a microscopic framework for interpreting [experimental trend] and suggest [test/design/control].

Scale ending:
> The simulations reveal [collective/rare/long-time behavior] that is inaccessible in conventional AIMD, opening a route to [prediction/design].

Reliability ending:
> The protocol provides practical criteria for reporting [property] with statistically meaningful confidence from AIMD/MD trajectories.

## Common Failures

- Starting with the model name instead of the scientific bottleneck.
- Listing methods without saying what they make possible.
- Reporting only force MAE when the claim is about diffusion, phase transition, thermal transport, spectra, or reactivity.
- Ending with an empty impact sentence such as "This work is important for materials design."
- Overclaiming beyond the validated domain.

## Final Check

After drafting, label each sentence by function: field, bottleneck, contribution, evidence, main result, implication. If two adjacent sentences perform the same function, compress them. If a function is missing, add it.
