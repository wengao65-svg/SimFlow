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
    "registered artifacts",
    "previous checkpoint"
  ],
  evidence_outputs: [
    "stage_manifest",
    "artifact_metadata",
    "handoff_notes"
  ],
  recommended_skills: skill ? [skill] : [],
  suggested_checks: [
    "inputs documented",
    "outputs registered",
    "lineage recorded"
  ],
  approval_triggers: [],
  handoff_notes: [
    "Record what changed, which artifacts support the result, and what remains uncertain."
  ],
  risk_notes: [],
  checkpoint_policy: "on_completion",
};

fs.writeFileSync(stageFile, JSON.stringify(template, null, 2));

console.log(`Stage created: ${stageName}`);
console.log(`  File: ${stageFile}`);
