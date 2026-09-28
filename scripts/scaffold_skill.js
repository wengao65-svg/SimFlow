#!/usr/bin/env node
/** Scaffold a portable SimFlow Skill without runtime or workflow ceremony. */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const [name, ...args] = process.argv.slice(2);
if (!name || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name)) {
  console.error('Usage: node scaffold_skill.js <lowercase-hyphen-name> [--description "description"]');
  process.exit(1);
}
const descriptionIndex = args.indexOf('--description');
const description = descriptionIndex >= 0 ? args[descriptionIndex + 1] : '';
const skillDir = path.join(ROOT, 'skills', name);
if (fs.existsSync(skillDir)) { console.error(`Skill already exists: ${name}`); process.exit(1); }
fs.mkdirSync(skillDir, { recursive: true });
const template = `---
name: ${name}
description: ${description || 'TODO: Explain this Skill and when it applies.'}
---

# ${name}

## Purpose

TODO: Describe the scientific work this Skill helps with.

## Task principles

- TODO: State decisions that materially improve the host agent's work.
- Keep user decisions, files, and records under user control.

## Minimum checks

- TODO: List input, unit, convergence, or evidence checks.

## Common failure modes

- TODO: Describe misleading outputs or unsupported claims.

## Escalate uncertainty when

- TODO: Identify ambiguity that needs the user or a domain expert.

## Completion criteria

- TODO: Define an evidence-bounded useful result.

## Optional references

Add focused references only when they materially change decisions.

Real execution follows the host permission system and the user's authorization
for the concrete action. This Skill does not create project state.
`;
fs.writeFileSync(path.join(skillDir, 'SKILL.md'), template);
console.log(`Skill created: ${skillDir}`);
