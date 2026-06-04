# Discussions and Conclusions

Use this guide to draft Discussion, Conclusion, or final Results paragraphs. The Discussion should interpret the evidence chain, define scope, and explain why the work changes the field.

## What Discussion Must Do

Discussion is not a second Results section. It should:

1. State the answer to the problem posed in the Introduction.
2. Explain what the result changes in current understanding or practice.
3. Integrate separate Results figures into one mechanism, workflow, or principle.
4. Define limitations and domain of validity.
5. Suggest concrete future experiments, simulations, or applications.
6. End with a calibrated final claim.

## Corpus Patterns

Nature-family papers often use a short `Discussion` or `Conclusion` after Results. The strongest examples restate the main finding, explain implications, acknowledge limits, and end with an enabled capability.

CHGNet-style method discussions move from field need, to what the model contributes, to applications, to remaining limitations in charge representation, and finally to a concise capability statement.

Graphene-style physical discussions explicitly define assumptions and scope before making broad claims. They discuss defects, substrate facets, functional limitations, and future experiments, then summarize the mechanism.

AIMD-statistics-style discussions are more procedural: they convert Results into practical rules and recommended reporting practice.

PR-style papers often use `Conclusions` rather than `Discussion`. They usually summarize the main computed findings and connect them to future measurements or theory.

## Six-Move Discussion Structure

Move 1: Answer.
> We have shown/established that [main claim].

Move 2: Evidence synthesis.
Combine the key figure outcomes without repeating all numbers.

Move 3: Mechanistic or methodological meaning.
Explain why the result happens or why the method works.

Move 4: Field implication.
State what prior interpretation, limitation, design rule, or simulation practice changes.

Move 5: Scope and limitations.
Name the conditions under which the claim is demonstrated and what remains outside scope.

Move 6: Forward-looking final sentence.
State a concrete capability, experiment, or application path.

## Type-Specific Discussion Guides

### Method Papers

Must include:

- What bottleneck is reduced: data cost, transferability, missing physics, MD stability, or uncertainty.
- Which evidence proves it: benchmark, ablation, learning curve, downstream MD, property validation.
- Where the method should not yet be trusted.
- What future data/model ingredients are needed.

Suggested structure:

1. Restate the method contribution.
2. Summarize accuracy and efficiency gains.
3. Explain why the new ingredient matters.
4. Discuss domain of applicability and failure modes.
5. End with the new simulation capability.

Avoid claiming a method is "universal" unless the demonstrated chemical and configurational space supports that word.

### Physical-Problem Papers

Must include:

- The resolved mechanism or interpretation.
- How the simulation distinguishes alternatives.
- How the result explains experiment or prior disagreement.
- Which real-world conditions could change the conclusion.
- What experiment could test the prediction.

Suggested structure:

1. State the physical answer.
2. Synthesize trajectory/spectral/thermodynamic evidence.
3. Contrast with previous interpretation.
4. Discuss defects, finite size, functional choice, timescale, or sample conditions.
5. End with a unified microscopic picture or design principle.

### Scale-Breakthrough Papers

Must include:

- Why the achieved scale changes the physics.
- What would be missed by small-cell or short-time simulations.
- Whether scale convergence has been checked.
- How the result can be tested or generalized.

Do not end with atom count. End with the phenomenon enabled by that scale.

### Reliability/Statistics Papers

Must include:

- Practical rules or thresholds.
- What common practice is misleading.
- How uncertainty should be reported.
- Which quantities or regimes the criterion applies to.

The Discussion should read like a decision guide for future simulations.

## Writing Limitations Well

A limitation should strengthen credibility by being specific and bounded.

Weak:
> There are some limitations in this work.

Stronger:
> Because the training set does not include [regime], the present potential should not be used to infer [property] under [condition] without additional validation.

Weak:
> More experiments are needed.

Stronger:
> Operando [measurement] under controlled [condition] would directly test the predicted [mechanism/signature].

## Final Paragraph Templates

Method:
> In summary, [method] provides [capability] by [new ingredient]. Together, the validation and downstream simulations show that [claim]. Future extensions should target [missing regime], but the present framework already enables [specific class of simulations].

Physical:
> In summary, our simulations identify [mechanism] as the origin of [phenomenon]. This resolves/explains [debate/observation] and suggests that [control variable] can be used to [design/test].

Reliability:
> In summary, reliable estimates of [quantity] require [criterion]. Reporting [uncertainty metric] alongside [value] will prevent [misinterpretation] and make AIMD/MD studies of [class] more reproducible.

## Common Failures

- Repeating every Results figure in order.
- Adding new unvalidated claims at the end.
- Hiding limitations in vague language.
- Ending with "this work provides insights" without naming the insight.
- Not returning to the problem stated in the Introduction.
- Treating model accuracy as the final message when the paper's real claim is physical.

## Final Check

After drafting, ask:

- What changed after this paper?
- What remains uncertain?
- What should the next experiment or simulation do?
- Would a skeptical reviewer know exactly where the claim is valid?
