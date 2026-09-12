# From Reviewed Evidence to Academic Narrative

Use when a draft sounds like an audit or progress report. Rebuild the argument
from the available evidence, not from acceptance labels. The examples below are
illustrative writing exercises, not results or quotations from the REE project.
Do not import their values or conclusions into a real manuscript.

## Evidence-Preserving Revision

Identify what the evidence actually says: observable, conditions, contrast,
uncertainty, and scope. Ask what scientific question that evidence addresses and
which explanation it supports or leaves open. Draft around that relationship.
Then compare with the original evidence for changed meaning, not just fluency.
No new acceptance report, prescribed table, or fixed paragraph formula is needed.

### Example: Coordination Thermodynamics

Supplied facts for this exercise only:

- At 300 K, defined states 8 and 9 have equilibrium population ratios
  P9/P8 = 2 for system A and P9/P8 = 0.5 for system B.
- Delta G = G9 - G8 = -kBT ln(P9/P8), with the same state definitions.
- Estimates are conditional on sampling those two states. Other states and
  transition rates were not established. No uncertainty estimate is supplied.

Audit-style draft:
> The relative free energies passed the acceptance checks for A and B. The
> accepted results support an 8/9 inversion. These are not global free energies
> and should not be interpreted as kinetic barriers.

Academic revision:
> The relative preference of the two coordination states reverses between A and
> B at 300 K. State 9 is twice as populated as state 8 in A, whereas its population
> is half that of state 8 in B. Accordingly, G9 - G8 changes from -kBT ln 2 to
> +kBT ln 2, linking the population redistribution to a reversal of the
> thermodynamic preference within the sampled two-state ensemble. This comparison
> does not determine the populations of other states or the exchange rates.

The revision states the positive finding and explains the relation between
populations and free energy. It does not invent a molecular cause, global
equilibrium, uncertainty, or a rate. For publication, missing uncertainty remains
an author query outside this paragraph; do not add "statistically significant".

### Example: Different Observables

Supplied facts for this exercise only: the mean coordination number changes
smoothly across a series, while a separately defined radial measure has a more
localized change. Their crossover locations differ under the stated definitions;
uncertainties and tests of coordinate sufficiency are not supplied.

Audit-style draft:
> Both descriptors passed the review, but the crossover was not accepted as
> universal. The scalar coordinate has limitations.

Academic revision:
> The two measures describe different aspects of the structural evolution: the
> mean coordination changes smoothly, whereas the radial measure changes over a
> narrower part of the series. Their distinct crossover locations therefore do
> not define a common transition point under the present definitions. These
> observations alone do not establish whether either scalar measure adequately
> distinguishes the underlying configurations.

Do not convert this contrast into evidence for a first-order transition, a
specific water-exchange mechanism, or proven coordinate failure. A statement
that one coordinate misses distinct configurations requires additional evidence.

### Example: A Material Exclusion

Supplied facts for this exercise only: a forward and reverse scan for condition
C give incompatible state populations; C is excluded from a quantitative
equilibrium comparison. No equilibrated population for C is available.

Academic expression:
> Forward and reverse scans at C yield incompatible populations, leaving the
> equilibrium preference unresolved there. The quantitative comparison is
> therefore restricted to the other sampled conditions.

Retain the exclusion and its reason. Do not replace it with "all conditions show
the trend", infer physical hysteresis from an unequilibrated calculation alone,
or hide C only in a technical appendix. Detailed scan diagnostics can be placed
in Methods or SI while the interpretive boundary remains visible.

## Corpus Contrasts, Not Universal Templates

The design basis is the 25 local PDFs reviewed in the PR (7) and Nature-family
(18) collections. Reading covered abstracts, section organization, representative
body passages and captions, with deeper reads of key examples. It was not a
verification of every scientific claim or external SI. Folder membership does
not establish publication status; the collection includes preprints.

The following locators make the contrasts recoverable if the original corpus is
available. They are optional source locations, not a required runtime layout.
Base directories in the reviewed installation:
`/mnt/d/Codex/lunwen/PR/` and
`/mnt/d/Codex/lunwen/Nature_theory_articles_public/`.

| Source filename (within the relevant directory) | Passage or contrast to inspect |
| --- | --- |
| `PhysRevB.110.024106-accepted.pdf` (PR) | PDF pp. 3-6: structural pairing motivates bond persistence, then spectroscopic and electronic interpretation; sensitivity checks accompany affected claims. |
| `npjComputMater_2024_DPA2_large_atomic_model_multitask_learner.pdf` | PDF pp. 6-7: remaining generalization error motivates fine-tuning, then computational cost motivates distillation. Workflow order can express an argument. |
| `NatCommun_2024_perturbed_neural_network_potentials_Efield.pdf` | PDF pp. 7-9: error structure and directional response explain why an observable can survive background error; specific method limits remain. |
| `npjComputMater_2018_AIMD_diffusion_statistical_variances.pdf` | PDF pp. 5-7: sampling variance, accessible regimes, and numbered practical guidance. Procedure is the contribution here, not the default prose style elsewhere. |
| `NatCommun_2021_DFT_macroscopic_QED_2D_materials.pdf` | Results and dedicated limitations passage, PDF pp. 3-6: approximation boundaries are central theoretical content. |
| `Nature_2024_AI2BMD_protein_molecular_dynamics.pdf` | PDF pp. 2-3: caption distinguishes reference levels and measured versus extrapolated timing. Necessary detail can justify long captions. |
| `NatCommun_2026_MLMD_graphene_hydrophobic.pdf` | Discussion opens with scope assumptions; a limitations-first passage can be scientifically appropriate. |
| `Finite-temperature thermally-assisted-occupation density-functional theory, ab initio molecular dynamics.pdf` (PR) | Theory development precedes computational details and applications; methods guidance must include derivation, not only MLP training. |
| `npjComputMater_2024_ab_initio_non_crystalline_structure_database_diffusivity.pdf` | PDF pp. 2-5: composition coverage and confounding motivate restricted comparisons and feature design. |
| `npjComputMater_2024_DPA1_pretraining_deep_learning_potential.pdf` | Three main figures and a short Discussion: no universal six-figure or six-move structure. |

The remaining corpus spans alumina, aluminum criticality, graphene thermoelectrics,
triply periodic minimal surfaces, sodium nitrite, combustion, water density correction,
TiO2 dissociation, spin defects, Ti3O5 transformation, GaN/BAs cooling, UNEP-v1,
long-range polarizable potentials, CHGNet, and GNoME. Its diversity supports
conditional guidance, not a single best manuscript order. Examples are not
quality certifications: do not inherit numerical typos, promotional rhetoric,
scientific claims, or assumed journal policies from them.

## Behavioral Revision Exercises

Use the supplied facts above as self-contained exercises when evaluating a change
to this Skill. Request only a Results paragraph, without providing the example
answer, and compare the output with the fact set. Also test a method-flow passage
and a requested reviewer response so that narrative guidance does not suppress
legitimate workflow logic or point-by-point review.

Assess whether the output:

- Makes the scientific relation, rather than an acceptance verdict, its subject.
- Preserves definitions, values, exclusions, and scope without new mechanisms.
- Explains the inference supported by the evidence and retains unresolved alternatives.
- Avoids both redundant disclaimers and concealed limitations.
- Adapts to the requested deliverable without mandatory figures or paragraph counts.

These are qualitative evaluation criteria, not proof of improved agent behavior
from a keyword test. Static validation can check packaging, not narrative quality.
