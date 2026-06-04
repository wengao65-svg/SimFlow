# Section Writing Index

Use this file as a compact entry point. For real drafting, load the specific section guide instead of relying on generic templates.

## Section Guides

- Abstracts: read `abstracts.md`.
- Introductions: read `introductions.md`.
- Results: read `results.md`.
- Discussions and conclusions: read `discussions.md`.
- Methods: read `methods.md`.
- Figure captions: read `figure-captions.md`.
- Reviewer response letters: use the reviewer response pattern below and `reviewer-checklist.md`.

## Corpus Basis

The section guides are distilled from local Nature, Nature Communications, Nature Machine Intelligence, npj Computational Materials, PRB, and arXiv/ChemRxiv papers in computational materials/physics, including DFT, AIMD, MD, MLP, active learning, foundation potentials, diffusion, phase transitions, transport, interfaces, and uncertainty analysis.

## One-Sentence Contribution

Method:
> We introduce X, a Y framework that enables Z by overcoming A.

Physical problem:
> We show that X occurs through Y, resolving Z.

Scale breakthrough:
> By extending simulations to X, we reveal Y that is inaccessible to conventional AIMD.

Reliability/statistics:
> We establish X, a criterion/procedure for quantifying Y in Z simulations.

## Abstract Template

Before drafting an abstract, read `abstracts.md`.

1. "Atomistic simulations are essential for [scientific/application area], but [specific bottleneck]."
2. "Existing [DFT/AIMD/classical MD/MLP] approaches are limited by [cost/accuracy/transferability/sampling/statistics]."
3. "Here we [introduce/show/develop] [main contribution]."
4. "We demonstrate [quantified evidence: accuracy, data efficiency, MD stability, agreement, uncertainty]."
5. "This enables [new simulation regime/physical conclusion/design principle/reliability protocol]."

## Introduction Paragraph Roles

Before drafting an introduction, read `introductions.md`.

Paragraph 1: Importance of the material/process/property.

Paragraph 2: Why atomistic simulation is needed and what conventional methods cannot do.

Paragraph 3: Progress and remaining gap in DFT/AIMD/MD/MLP-MD.

Paragraph 4: Specific unresolved problem or methodological bottleneck.

Paragraph 5: What this paper contributes, with a concise preview of evidence and impact.

## Results Opening

Before drafting Results, read `results.md`.

Start each Results subsection with the question it answers:

- "We first establish whether the training set covers the relevant configuration space."
- "We next test whether the model remains stable under the thermodynamic conditions used for production MD."
- "Having validated the potential, we examine the microscopic origin of..."

## Discussion Closing

Before drafting Discussion or Conclusion, read `discussions.md`.

End with calibrated scope:

- What the work enables.
- What physical or methodological insight changes.
- What conditions remain outside the demonstrated domain.
- What experimental or computational test could follow.

## Figure Caption Pattern

Before writing captions, read `figure-captions.md`.

1. State what the figure demonstrates.
2. Define panels and simulation conditions.
3. Mention reference/baseline.
4. State the takeaway, not just what is plotted.

## Methods Pattern

Before drafting Methods or checking reproducibility, read `methods.md`.

1. State reference electronic-structure settings.
2. Define datasets, filtering, train/test split, and labels.
3. Specify MLP architecture/training/active learning if used.
4. Specify MD/enhanced-sampling/property-calculation protocols.
5. Define uncertainty/statistics and availability of data/code.

## Reviewer Response Pattern

1. Thank the reviewer briefly.
2. Restate the concern in scientific terms.
3. Describe the new analysis or clarification.
4. Point to exact manuscript location.
5. Explain how the change affects or does not affect the conclusion.
