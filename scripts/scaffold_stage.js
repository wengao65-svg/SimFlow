#!/usr/bin/env node
/**
 * Scaffold a new SimFlow workflow stage contract.
 * Usage: node scaffold_stage.js <stage-name> [--description "description"] [--skill "skill_name"]
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const STAGES_DIR = path.join(ROOT, 'workflow/stages');

const args = process.argv.slice(2);
const stageName = args[0];

if (!stageName) {
  console.error('Usage: node scaffold_stage.js <stage-name> [--description "description"] [--skill "skill_name"]');
  process.exit(1);
}

const descIdx = args.indexOf('--description');
const skillIdx = args.indexOf('--skill');
const description = descIdx >= 0 && args[descIdx + 1] ? args[descIdx + 1] : '';
const skill = skillIdx >= 0 && args[skillIdx + 1] ? args[skillIdx + 1] : '';

const stageFile = path.join(STAGES_DIR, `${stageName}.json`);
if (fs.existsSync(stageFile)) {
  console.error(`Stage already exists: ${stageName}`);
  process.exit(1);
}

const template = {
  name: stageName,
  description: description || `Open stage contract: ${stageName}`,
  intent: description || `Describe the research intent for ${stageName}.`,
  acceptable_inputs: [
    "user-provided files",
    "existing project evidence",
    "optional recovery checkpoint"
  ],
  evidence_outputs: [
    "logical deliverable",
    "provenance summary",
    "remaining uncertainty"
  ],
  recommended_skills: skill ? [skill] : [],
  suggested_checks: [
    "inputs documented",
    "outputs verified",
    "provenance documented"
  ],
  approval_triggers: [],
  handoff_notes: [
    "Summarize what changed, which evidence supports the result, and what remains uncertain."
  ],
  risk_notes: [],
};

fs.writeFileSync(stageFile, JSON.stringify(template, null, 2));

console.log(`Stage created: ${stageName}`);
console.log(`  File: ${stageFile}`);
