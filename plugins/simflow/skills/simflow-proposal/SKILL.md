---
name: simflow-proposal
description: Guide computational research question formulation, protocol design, validation criteria, alternatives, and cost-aware experimental planning.
---

# Research Proposal

## Purpose

Turn a scientific goal into a bounded, testable computational plan without
inflating it into an unnecessary pipeline or hiding critical assumptions.

## Use when

- The user is choosing methods, observables, baselines, or validation criteria.
- Several computational routes are plausible and need comparison.
- A large calculation should be decomposed into lower-cost decisions.

## Do not use when

- The user has already fixed the protocol and only wants execution help.
- The immediate task is inspection or interpretation of existing outputs.
- The task is a minor local edit that does not change scientific intent.

## Task principles

- Define the research question before selecting software or workflow steps.
- Separate required calculations from optional extensions.
- Name the observable that answers each question.
- Establish a baseline and explicit acceptance or rejection criteria.
- Prefer low-cost discriminating tests before expensive production work.
- List assumptions, alternatives, dependencies, and stopping conditions.
- Do not make proposal work a mandatory prerequisite for unrelated tasks.

## Minimum checks

- Research question and intended scientific claim are explicit.
- Inputs, observables, comparison groups, and reference states are identified.
- Validation criteria are measurable rather than qualitative placeholders.
- Cost, scale, convergence, and data availability risks are considered.
- The plan distinguishes preparation, diagnostic runs, production runs, and
  analysis.

## Common failure modes

- Choosing software before clarifying the scientific question.
- Designing one large pipeline with no intermediate decision points.
- Treating a method name as a validation strategy.
- Omitting negative controls, baselines, or reference states.
- Assuming missing parameters or user intent without marking the assumption.

## Escalate uncertainty when

- Different assumptions lead to materially different computational protocols.
- The requested claim cannot be supported by the proposed observables.
- Resource limits, proprietary inputs, or real execution constraints are unclear.

## Completion criteria

- Each proposed calculation has a stated purpose and decision consequence.
- The minimal viable path is distinguishable from optional follow-up work.
- Assumptions, risks, validation criteria, and unresolved choices are visible.

## Optional references

Use task-specific literature, domain skills, and project evidence only when they
materially inform the protocol. Avoid loading every potentially related skill.
