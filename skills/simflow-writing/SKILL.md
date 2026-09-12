---
name: simflow-writing
description: Guide the planning, drafting, revision, and review of computational materials and physics manuscripts so their claims, methods, figures, validation, uncertainty, and limitations remain faithful to the available evidence.
---

# Computational Simulation Writing

## Purpose

Turn computational research evidence into academic narrative organized around
scientific questions, observed phenomena, and evidence-bounded explanations.
Evidence review determines what can be said; it does not prescribe the order
or vocabulary of the manuscript. Write about what the results mean, not merely
which calculations or checks were completed.

## Task principles

1. Identify the scientific question and contribution: physical understanding,
   theory or method, data/resource, reliability/statistics, or a combination.
   Treat scale as a contribution dimension, not a compulsory paper category.
   These distinctions help select guidance; they do not fix the paper structure.
2. Formulate the main answer in language specific to the system and evidence.
   A descriptive finding, constrained interpretation, or unresolved alternative
   can be the contribution. Do not manufacture a mechanism or resolved debate.
3. Plan the argument around what each result establishes and what the reader
   needs to understand next. Figures and rough plots can expose this logic;
   neither a figure-first workflow nor a fixed figure count is required.
4. Distinguish the roles of method validation and physical discovery without
   requiring separate figures or sections. The same evidence can serve both.
   Verify evidence before drafting, but do not require validation-first prose.
5. Every substantive claim must be supportable by available results, figures,
   tables, sources, or explicit user-provided facts. Describe methods as executed,
   not as planned. Never invent settings, citations, sampling, uncertainty,
   reproducibility details, or missing results.
6. Distinguish observation, interpretation, hypothesis, and speculation. Do not
   turn a trend into a mechanism or correlation into causation. Explain the
   reasoning connecting evidence and interpretation, including viable alternatives.
7. Build transitions from scientific dependencies: an observation raises a
   question, a comparison distinguishes interpretations, or a remaining problem
   motivates the next analysis. Do not invent dependencies or force every
   paragraph into a question-observation-explanation formula.
8. Keep internal acceptance labels and audit checklists out of manuscript prose
   unless the criteria themselves are the scientific subject. Express the
   quantity, comparison, uncertainty, and consequence instead. Reconstruct the
   argument rather than simply replacing words such as "accepted" or "validated".
9. Retain exclusions, negative evidence, and limits that affect interpretation.
   State their scientific consequence near the affected claim; place supporting
   technical detail in Methods or SI as appropriate. Do not conceal limitations
   for fluency or repeat generic disclaimers in every subsection.
10. For interatomic potentials, energy, force, and stress errors are necessary
    but insufficient evidence where those quantities are relevant. Relate
    validation to the observable and deployment regime, including MD stability
    and property validation when dynamic applications are claimed. Do not let
    "DFT accuracy with MD efficiency" stand as the whole novelty.
11. Distinguish in-distribution accuracy, interpolation, extrapolation, and
    downstream transfer. Account for finite-size, finite-time, equilibration,
    independent sampling, and uncertainty where they affect the claim. Never
    generalize beyond the tested chemical, structural, thermodynamic, or temporal domain.
12. Use reference papers as examples of reasoning and organization, not wording
    to copy or scientific authority for the current results. Select examples
    relevant to the contribution; do not impose journal-family stereotypes.

For planning, focus on the question, provisional answer, and relationships among
results. Offer a figure plan or outline when useful. Keep evidence gaps distinct
from the proposed narrative; do not automatically append a reviewer report.

For drafting, produce academic prose in the requested language and section scope,
not an audit summary. Use explicit placeholders only for essential missing
details, with unresolved author queries outside the manuscript. Narrow or
withhold claims when their supporting evidence is missing.

For revision, preserve scientific meaning, numbers, definitions, uncertainty,
citations, and scope. Improve argumentative order as well as sentences. If an
existing claim is unsupported, flag and calibrate it rather than preserving an
error or silently introducing a different scientific conclusion.

## Minimum checks

- The question and main answer agree with the available evidence.
- Each central claim maps to evidence; figures and tables have intelligible
  argumentative roles without a prescribed sequence or count.
- The prose explains observations, contrasts, and consequences rather than
  treating passed checks or completed tasks as the scientific result.
- Validation is connected to the affected claim, whether integrated or separate.
- Methods report the relevant executed settings, reference states, estimators,
  exclusions, and sampling or uncertainty procedures without inventing checks.
- Values, units, labels, significant figures, definitions, and citations agree
  across prose, figures, tables, captions, and supplements.
- Strong terms such as mechanism, convergence, transferability, robustness,
  generality, and production readiness match the actual evidence.
- Failed or incomplete calculations are disclosed when they affect interpretation.
- Follow supplied journal requirements, not assumed rules inferred from examples.

## Common failure modes

- Polishing prose before knowing the relevant trends and uncertainties.
- Imposing a contribution type, paragraph formula, or figure sequence on all papers.
- Turning internal review outcomes into the subject of Results or Discussion.
- Replacing audit vocabulary while leaving a checklist-shaped argument intact.
- Inventing causal bridges, resolved controversies, or future predictions for fluency.
- Hiding negative evidence or relocating a crucial limitation where readers miss it.
- Repeatedly defending a narrow result instead of stating its positive finding
  and the particular inference it does not support.
- Treating force errors, one snapshot, or one rare event as sufficient evidence
  for broad physical or dynamical claims.
- Using obsolete results or describing the intended protocol instead of execution.

## Escalate uncertainty when

- The requested claim exceeds the available evidence or validation domain.
- The question or contribution is unclear enough to change the argument.
- Methods, values, figure versions, reference states, or uncertainty estimates conflict.
- Sampling or model limitations prevent the proposed interpretation.
- Authorship, confidentiality, or publication requirements affect the deliverable.

## Completion criteria

- The requested text develops a scientific question, observation, or explanation
  with a coherent claim-evidence chain, not a record of audit completion.
- Claims, methods, figures, values, citations, and limitations remain consistent.
- Unsupported statements are removed, weakened, or explicitly marked, with
  evidence needs identified separately when stronger claims would require them.
- Observations remain distinguishable from interpretations and hypotheses.
- Necessary limitations are retained without redundant defensive prose.
- Missing details needed to finalize the text are identified outside the prose.

## Optional references

Load only the contribution and section guidance needed for the task:

- `references/narrative-examples.md`: audit-to-narrative revision, corpus contrasts,
  and evidence-preserving examples; read when prose sounds like a report.
- `references/physical-problem-paper.md`: physical questions and competing explanations.
- `references/method-paper.md`: theory, derivation, computational methods, MLPs,
  training, sampling, active learning, and foundation potentials.
- `references/data-resource-paper.md`: databases, reference datasets, coverage,
  reusable resources, and sampling or compositional bias.
- `references/scale-breakthrough-paper.md`: scale-dependent contributions across types.
- `references/reliability-statistics-paper.md`: uncertainty and sampling as the contribution.
- `references/section-templates.md`: section-level writing choices and routing,
  not mandatory templates.
- `references/abstracts.md`: abstract drafting and revision.
- `references/introductions.md`: scientific context, prior work, and the open question.
- `references/results.md`: evidence-to-explanation logic and transitions.
- `references/discussions.md`: synthesis, implications, scope, and conclusions.
- `references/methods.md`: executed methods and reproducibility details.
- `references/figure-captions.md`: interpretable figures and conditional detail.
- `references/reviewer-checklist.md`: requested review or final evidence checks,
  not a default drafting outline.

Neither all references nor the original local paper collection is a prerequisite
for ordinary drafting. This Skill provides guidance, not runtime or project-state
requirements.
