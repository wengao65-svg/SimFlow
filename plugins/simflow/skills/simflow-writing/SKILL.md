---
name: simflow-writing
description: Guide the planning, drafting, revision, and review of computational materials and physics manuscripts so their claims, methods, figures, validation, uncertainty, and limitations remain faithful to the available evidence.
---

# Computational Simulation Writing

## Purpose

Help the agent turn DFT, AIMD, classical MD, machine-learning-potential,
MLP-MD, active-learning, transport, interface, phase-transition, and related
simulation evidence into a coherent scientific manuscript. Anchor the writing
on the paper's claim, evidence chain, and figure logic before polishing prose.

## Use when

- Planning, outlining, drafting, revising, or reviewing a computational
  materials or physics manuscript.
- Writing abstracts, introductions, results, discussions, conclusions,
  methods, figure captions, cover letters, or reviewer responses.
- Deciding whether a paper is primarily a method, physical-problem,
  scale-breakthrough, reliability/statistics, or deliberately hybrid
  contribution.
- Auditing whether scientific claims, numerical statements, figures, and
  reproducibility details are supported and mutually consistent.
- Writing in English or supporting Chinese-language manuscript discussion.

## Do not use when

- The primary task is new literature discovery, model construction,
  computation, or analysis rather than writing from available evidence.
- Evidence needed for the requested claim has not yet been produced; identify
  the missing evidence instead of drafting the claim as established fact.
- The user needs journal-specific submission rules that are not available in
  the provided material or verified current sources.

## Task principles

1. Identify the manuscript type: method, physical-problem,
   scale-breakthrough, reliability/statistics, or a deliberate hybrid with one
   clearly dominant contribution.
2. State the one-sentence contribution in the form: "We show/introduce X,
   which enables Y by overcoming Z." Calibrate each part to demonstrated
   evidence.
3. Prefer figure-first planning. Build a claim-evidence map, a 5-6 figure
   storyboard when appropriate, and rough analysis plots before drafting full
   sections. Ask which figure or table supports each central claim.
4. Separate method validation from physical discovery. Make clear which
   results establish trust in the computational approach and which results
   deliver the new scientific finding.
5. Every substantive claim must be supportable by available results, figures,
   tables, sources, or explicit user-provided facts.
6. Describe methods as executed, not as originally planned. Never invent
   parameters, software versions, citations, sampling, uncertainty estimates,
   or reproducibility details.
7. Distinguish observed results, interpretation, hypothesis, and speculation.
   Do not turn a trend into a mechanism or correlation into causation.
8. Do not let "DFT accuracy with MD efficiency" stand as the whole novelty.
   State the capability, regime, scale, reliability result, or physical
   conclusion that becomes possible.
9. Treat energy, force, and stress errors as necessary but insufficient for an
   interatomic potential. Calibrate claims using MD stability and physically
   meaningful property validation.
10. Distinguish in-distribution accuracy, interpolation, extrapolation, and
    downstream transfer. Do not generalize beyond the tested chemical,
    structural, thermodynamic, or temporal regime.
11. For trajectory-derived quantities, account for finite-size and finite-time
    effects, independent trajectories or seeds, equilibration, sampling, and
    uncertainty when they matter to the claim.
12. Use local reference papers as style and structure examples without copying
    wording or inheriting unsupported claims.

When the user asks to discuss or plan a manuscript, normally provide the
manuscript type, one-sentence contribution, figure plan, section outline, key
validation requirements, and likely reviewer concerns. Adapt the shape when
the user requests a narrower deliverable.

When the user asks to draft, produce polished scientific prose in the requested
language. Use explicit placeholders only where evidence or metadata is
missing, and list what is needed to remove them.

When the user asks to revise, preserve the scientific claim unless asked to
change it. Improve logic, specificity, transitions, evidence alignment, and
claim calibration without silently adding new facts.

## Minimum checks

- The manuscript type and one-sentence contribution agree with the strongest
  available evidence.
- Every central claim maps to a result, figure, table, source, or explicit user
  fact; each planned figure has a clear argumentative role.
- Validation figures establish trust separately from figures that present the
  new scientific result.
- The introduction starts from the scientific bottleneck rather than merely
  the software or model name.
- Methods include the relevant reference standard and executed settings, such
  as functional, dispersion treatment, Hubbard U, pseudopotential, cutoff,
  k-point scheme, thermostat or barostat, timestep, ensemble, cell size,
  trajectory length, seeds, and uncertainty method.
- Numerical values, units, labels, significant figures, uncertainty, and
  definitions agree across prose, figures, captions, tables, and supplements.
- Baselines, sampling adequacy, MD stability, property validation, uncertainty,
  and reproducibility are sufficient for the strength of the claims.
- Failed, excluded, or incomplete calculations are disclosed when they affect
  the scientific record or interpretation.
- Strong terms such as mechanism, convergence, transferability, robustness,
  generality, or production readiness meet an explicit evidence threshold.
- The requested journal style is followed only to the extent it is known or
  supplied; scientific accuracy takes precedence over stylistic imitation.

## Common failure modes

- Drafting polished sections before the central claim and figure logic are
  stable.
- Treating a hybrid paper as several equal stories instead of choosing a
  dominant contribution.
- Writing the intended protocol instead of the executed protocol.
- Presenting test-set errors as sufficient evidence of stable or transferable
  MD behavior.
- Claiming novelty only from speed or scale without showing the newly enabled
  science or reliability result.
- Presenting a plausible explanation as an established mechanism.
- Ignoring finite-size, finite-time, seed-to-seed, or statistical uncertainty
  in trajectory-derived properties.
- Copying a number from an obsolete run, table, or figure revision.
- Removing failed calculations or negative evidence that constrain the
  interpretation.
- Using polished prose to conceal missing evidence, weak baselines, or unclear
  computational settings.

## Escalate uncertainty when

- A requested claim is stronger or broader than the available validation.
- The manuscript type or dominant contribution remains ambiguous and would
  materially change the figure plan or section logic.
- Methods, numerical values, figure versions, or uncertainty estimates conflict
  across sources.
- The reference standard, baseline, sampling protocol, or validation regime is
  unclear enough to affect reproducibility or scientific interpretation.
- Authorship, confidential content, target-journal requirements, or publication
  scope is unclear and materially affects the deliverable.

## Completion criteria

- The manuscript has a clear primary type, a calibrated one-sentence
  contribution, and a coherent claim-evidence chain.
- Claims, methods, figures, captions, numerical values, and limitations are
  mutually consistent.
- Method validation and physical discovery have distinct, intelligible roles.
- Unsupported statements are removed, weakened, or explicitly marked, with
  clearly identified evidence needs where stronger wording would require more
  support.
- The document distinguishes observed results from interpretation,
  hypothesis, and speculation.
- Missing data or metadata required to finalize placeholders are listed
  explicitly.

## Optional references

Load only the references relevant to the current manuscript type or writing
task:

- `references/method-paper.md`: new MLPs, training workflows, sampling,
  active learning, pretraining, foundation potentials, uncertainty, or
  general-purpose potentials.
- `references/physical-problem-paper.md`: manuscripts whose main claim resolves
  a materials or physics question.
- `references/scale-breakthrough-paper.md`: larger systems, longer times, or
  more realistic thermodynamic or chemical conditions than DFT or AIMD can
  reach directly.
- `references/reliability-statistics-paper.md`: statistical error, sampling
  adequacy, uncertainty, confidence, reproducibility, or reliability criteria.
- `references/section-templates.md`: section-level structure and contribution
  templates.
- `references/abstracts.md`: abstract drafting or revision.
- `references/introductions.md`: introduction drafting or revision.
- `references/results.md`: Results drafting from processed evidence and rough
  plots.
- `references/discussions.md`: Discussion and Conclusion drafting.
- `references/methods.md`: Methods drafting and reproducibility checks.
- `references/figure-captions.md`: figure caption drafting and review.
- `references/reviewer-checklist.md`: final manuscript review.

For a hybrid manuscript, load the primary manuscript-type reference first,
then only the section reference needed for the current task.
