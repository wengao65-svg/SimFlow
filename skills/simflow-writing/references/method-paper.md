# Theory and Method Contributions

Use for new theory, derivations, electronic-structure approximations, estimators,
sampling methods, algorithms, MLP architectures, or training strategies. Do not
equate a method contribution with an MLP benchmark-and-deployment sequence.

## Organize Around the New Ingredient

Identify the approximation, representation, algorithmic choice, or computational
obstacle at issue. Explain what changes and what consequence is demonstrated.
Choose evidence that distinguishes the proposed explanation of improvement from
other changes in data, capacity, reference level, or computational budget.

Theory may proceed through assumptions, derivation, limiting cases, and numerical
consequences. A training method may proceed through controlled comparisons,
remaining generalization error, fine-tuning, and cost reduction. A sampling method
may center on explored states, estimator bias, and access to rare events. These
are possibilities, not compulsory section orders or figure inventories.

Put equations or implementation details in the main argument when they carry the
new idea. Supporting derivations can go in SI, but do not exile the theoretical
contribution merely to make the paper resemble an application study.

## Match Evidence to the Claim

- For derivations, state assumptions, approximation order, applicable limits,
  and consistency checks; separate formal results from numerical demonstrations.
- For claimed improvement, use relevant baselines or controlled comparisons.
  Ablation is useful when attributing a gain to a component, not a mandatory
  experiment for every kind of theory.
- For MLPs, distinguish data coverage, held-out accuracy, transfer, and downstream
  behavior. Report relevant subset errors and properties, not just global MAE.
- For dynamic deployment claims, inspect stability and the target observables;
  static accuracy alone is insufficient. Do not require long MD for a method
  whose contribution is unrelated to dynamics.
- For efficiency claims, identify comparable hardware, workloads, reference
  accuracy, data-generation cost, and whether timings are measured or extrapolated.
- Explain known failure modes and their consequences. A dedicated limitations
  section is appropriate when approximation scope is central to the method.

## Narrative Check

Does each benchmark answer why the method works, where it works, or what it
enables? Remaining generalization error may motivate fine-tuning, and cost may
motivate compression; in theory work, formal development may itself be the
contribution. Neither requires a fixed six-figure storyboard.
