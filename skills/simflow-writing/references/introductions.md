# Introductions

Use this guide to draft or revise Introductions for DFT/AIMD/MD/MLP-MD papers. The goal is to build a narrowing argument from field importance to the exact contribution.

## What the Introduction Must Do

The Introduction must answer four questions before the Results begin:

1. Why should the reader care about this material, process, or simulation capability?
2. What is currently unknown, disputed, too expensive, or unreliable?
3. Why do existing experimental and computational approaches fail to close the gap?
4. What does this paper do that changes the situation?

Do not begin with a catalog of software, functionals, model names, or equations unless the paper is explicitly a theory-method paper and the equation is the bottleneck.

## Corpus Patterns

Nature-family introductions often have no explicit `Introduction` heading. The first body paragraph begins immediately after the abstract and narrows quickly from broad significance to the paper's specific gap.

npj and PR papers more often use explicit `INTRODUCTION` or `I. INTRODUCTION` headings. They allow more literature review, but strong papers still move toward a precise gap rather than a historical survey.

Method papers in the corpus use this sequence: importance of PES or atomistic simulation, DFT cost and empirical-potential limits, MLP progress, remaining model/data/physics bottleneck, then the proposed method.

Physical-problem papers use this sequence: importance of material/process, experimental ambiguity or unresolved mechanism, why conventional simulations are insufficient, validated simulation strategy, then the claimed mechanism.

Reliability papers use this sequence: widespread use of a computed quantity, short-trajectory/statistical limitation, failure of common practice, proposed uncertainty/procedure.

## Five-Paragraph Structure

Paragraph 1: Field and stakes.
Open with the material/process/property, not the tool. Establish the application or fundamental problem.

Paragraph 2: Why atomistic simulation is needed.
Explain what cannot be directly measured or inferred. Introduce DFT/AIMD/MD only as needed.

Paragraph 3: Existing progress.
Summarize the best current approaches in a way that sets up the gap. For MLP papers, mention recent universal/foundation/active-learning potentials only to define what remains unsolved.

Paragraph 4: Specific gap.
Name the exact missing capability, not a broad weakness. Examples: no reliable long-time MD for charged transition-metal oxides; local MLPs miss polarizable long-range interactions; AIMD diffusion estimates lack event-count-based uncertainty.

Paragraph 5: This work.
State the contribution, evidence route, and implication. This paragraph should foreshadow the figure order.

For short Nature-style introductions, merge Paragraphs 2 and 3. For PR-style introductions, Paragraph 3 may be longer but must end with the gap.

## Paragraph-Level Writing Instructions

### Paragraph 1: Field and Stakes

Sentence 1 should be broad but not vague:
> [Material/process/property] is central to [application/fundamental question] because [specific reason].

Sentence 2 should specify the atomistic feature:
> Its performance depends on [diffusion, phase transformation, interfacial water structure, charge transfer, thermal transport, defect dynamics].

Sentence 3 can introduce the unresolved need:
> A microscopic understanding of [feature] is therefore required to [predict/design/interpret].

Avoid opening with:
> Molecular dynamics is a powerful tool...

Use that sentence only after the scientific need is established.

### Paragraph 2: Simulation Need and Limits

State the method tension:

- DFT/AIMD gives electronic-structure fidelity but is limited in time/size.
- Empirical force fields are efficient but may fail for new chemistry, bond breaking, charge/spin, polarization, interfaces, or high-T/P conditions.
- Experiments may measure averages, spectra, or macroscopic trends without resolving microscopic pathways.

Do not write a generic "DFT is expensive" sentence. Tie the cost to the required phenomenon:
> Resolving [rare event/domain growth/diffusion statistics/interface reconstruction] requires [nanoseconds/many trajectories/large cells], whereas direct AIMD is limited to [typical scale].

### Paragraph 3: Progress and Remaining Gap

Give credit to existing work, then isolate the limitation.

Good structure:
1. Existing method class has enabled X.
2. However, it remains limited in Y.
3. This limitation matters because Y controls the main claim.

For method papers:
> Recent universal/foundation MLPs have expanded chemical coverage, but [target physics/domain] remains difficult because [label inconsistency, missing charge, long-range interactions, MD smoothness, data efficiency].

For physical papers:
> Previous experiments/simulations suggest [candidate explanations], but they cannot distinguish [alternative A] from [alternative B].

For reliability papers:
> Existing analyses often report fitting quality, but the fitted slope can be precise while the underlying number of diffusion events remains insufficient.

### Paragraph 4: Specific Gap

This is the most important paragraph. It should contain one gap sentence that could motivate the entire paper.

Template:
> What remains missing is [capability/criterion/mechanism] that can [action] under [conditions] with [required reliability].

Examples:

- What remains missing is a data-efficient training strategy that can transfer from representative low-order compositions to complex multicomponent alloys while remaining stable in production MD.
- What remains missing is an atomistic explanation that separates intrinsic wettability from substrate-induced and intercalated-water spectral signatures.
- What remains missing is a practical criterion that links AIMD trajectory length and diffusion-event count to uncertainty in diffusivity and activation energy.

### Paragraph 5: This Work

Use a compact "Here..." paragraph. It should not read like a table of contents, but it should preview the evidence chain.

Method:
> Here we introduce [method/model/workflow]. We first [dataset/architecture], then [validation/baseline], and finally [MD deployment/application]. The results show [quantified gain] and enable [domain].

Physical:
> Here we use [validated simulation approach] to show [main physical conclusion]. By combining [analysis 1] and [analysis 2], we identify [mechanism] and explain [experimental/theoretical observation].

Scale:
> Here we extend atomistic simulations to [scale/condition] using [validated approach], revealing [phenomenon]. The resulting [map/law/mechanism] cannot be obtained from conventional AIMD-scale simulations.

Reliability:
> Here we establish [procedure/statistical model] for [quantity]. We show that [common practice] fails when [condition], and provide [criterion] for reliable reporting.

## How to Use References

Do not pile citations after every sentence. Group them by function:

- field importance
- experimental observations/debate
- existing simulation methods
- known limitations
- benchmark/reference values

Each citation cluster should support one sentence function. If a paragraph has many citations but no gap, rewrite.

## Common Failures

- The Introduction sounds like a textbook review.
- The gap is "MLP has limitations" instead of a specific missing capability.
- The final paragraph lists every result without hierarchy.
- The paper's real novelty appears only in the Results, not in the Introduction.
- The same claim is made in the abstract and introduction without more precision.

## Final Check

After drafting, write the one-sentence gap and one-sentence contribution under the Introduction. If they are not obvious from Paragraphs 4-5, revise before writing Results.
