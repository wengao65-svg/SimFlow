---
name: simflow-writing
description: Guide computational research writing so claims, methods, figures, and limitations remain faithful to the available evidence.
---

# Scientific Writing

## Purpose

Help the agent draft and revise computational research text without separating
the narrative from what was actually calculated, analyzed, and observed.

## Use when

- Drafting or revising methods, results, discussion, captions, abstracts, or
  technical reports from existing evidence.
- Auditing whether claims and numerical statements are supported.
- Preparing a reproducible description of computational work.

## Do not use when

- The task primarily requires new literature discovery, modeling, computation,
  or analysis.
- Evidence needed for the requested claim has not yet been produced.

## Task principles

- Every substantive claim must be supportable by available results or sources.
- Describe methods as executed, not as originally planned.
- Distinguish results, interpretation, hypothesis, and speculation.
- Do not turn a trend into a mechanism or correlation into causation.
- Keep figure, table, and prose values consistent.
- Report failed, excluded, or incomplete calculations when they affect the
  scientific record.
- Avoid invented parameters, software versions, citations, or reproducibility
  details.

## Minimum checks

- Claims can be traced to a result, figure, table, source, or explicit user fact.
- Methods include the choices needed to understand and reproduce the work.
- Numerical values, units, labels, and uncertainty agree across the document.
- Limitations and negative evidence are not hidden.
- Strong language such as mechanism, convergence, transferability, or
  production readiness matches the evidence threshold.

## Common failure modes

- Writing the intended protocol instead of the executed protocol.
- Presenting a plausible explanation as an established mechanism.
- Copying a number from an obsolete run or figure revision.
- Removing failed calculations that constrain interpretation.
- Using polished prose to conceal missing evidence.

## Escalate uncertainty when

- A requested claim is stronger than the available evidence.
- Methods or numerical values conflict across sources.
- Authorship, journal style, confidential content, or publication scope is
  unclear and materially affects the deliverable.

## Completion criteria

- Claims, methods, figures, and limitations are mutually consistent.
- Unsupported statements are removed, weakened, or explicitly marked.
- The document distinguishes observed results from interpretation.

## Optional references

- `references/method-paper.md`
- `references/physical-problem-paper.md`
- `references/scale-breakthrough-paper.md`
- `references/reliability-statistics-paper.md`
- `references/section-templates.md`
- `references/abstracts.md`
- `references/introductions.md`
- `references/results.md`
- `references/discussions.md`
- `references/methods.md`
- `references/figure-captions.md`
- `references/reviewer-checklist.md`

Load only the references relevant to the current writing task.
