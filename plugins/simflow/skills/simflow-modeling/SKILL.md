---
name: simflow-modeling
description: Guide construction and transformation of scientifically meaningful computational models, structures, boundaries, and reference states.
---

# Scientific Modeling

## Purpose

Help the agent translate a scientific question into a defensible computational
object before engine-specific input details are considered.

## Use when

- Building or transforming structures, supercells, defects, surfaces,
  interfaces, solvated systems, or constrained models.
- Deciding composition, charge, periodicity, cell size, or initial geometry.
- Reviewing whether an existing model represents the intended physical system.

## Do not use when

- The model is fixed and the task only concerns engine syntax or execution.
- The user only wants analysis of completed outputs.

## Task principles

- Preserve user-provided source models and never silently replace them.
- State what physical object the model represents and what it omits.
- Do not change stoichiometry, charge, spin, boundary conditions, or constraints
  without scientific justification.
- Match cell size and model resolution to the target property and length scale.
- Define reference states for defects, surfaces, interfaces, adsorption, and
  charged systems.
- Prefer existing validated project conventions over rebuilding the model from
  a generic template.

## Minimum checks

- Elements, atom counts, composition, charge, and periodicity are consistent.
- Cell vectors, vacuum, minimum distances, overlaps, and obvious geometry
  defects are inspected.
- Supercell and sampling choices are adequate for the intended observable.
- Transformations are reproducible and source-to-derived relationships are
  clear.
- Ambiguous occupations, disorder, protonation, magnetism, or constraints are
  surfaced rather than guessed.

## Common failure modes

- Defaulting an ambiguous request to a bulk static model.
- Building a visually plausible structure with incorrect chemistry or charge.
- Applying periodic boundaries to an isolated or interfacial problem without
  checking image interactions.
- Treating a convenient initial configuration as a representative ensemble.
- Losing the original user model during conversion.

## Escalate uncertainty when

- Composition, protonation, charge, spin, disorder, or boundary conditions are
  scientifically underdetermined.
- Multiple reference states would change the final comparison.
- A requested transformation may invalidate existing validated parameters.

## Completion criteria

- The model's physical meaning, assumptions, and limitations are explicit.
- Structural sanity checks pass or failures are reported.
- Derived models remain traceable to their sources and transformations.

## Optional references

Use a Domain Skill only when software- or method-specific model semantics are
needed. Builders such as ASE or pymatgen are optional tools, not mandatory paths.
