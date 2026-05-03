#!/usr/bin/env node
/**
 * Scaffold a new SimFlow workflow stage.
 * Usage: node scaffold_stage.js <stage-name> [--description "description"] [--agent "agent_name"]
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const STAGES_DIR = path.join(ROOT, 'workflow/stages');

const args = process.argv.slice(2);
const stageName = args[0];

if (!stageName) {
  console.error('Usage: node scaffold_stage.js <stage-name> [--description "description"] [--agent "agent_name"]');
  process.exit(1);
}

const descIdx = args.indexOf('--description');
const agentIdx = args.indexOf('--agent');
const description = descIdx >= 0 && args[descIdx + 1] ? args[descIdx + 1] : '';
const agent = agentIdx >= 0 && args[agentIdx + 1] ? args[agentIdx + 1] : '';

const stageFile = path.join(STAGES_DIR, `${stageName}.json`);
if (fs.existsSync(stageFile)) {
  console.error(`Stage already exists: ${stageName}`);
  process.exit(1);
}

const template = {
  name: stageName,
  description: description || `New stage: ${stageName}`,
  default_agent: agent || '',
  default_skill: `simflow-${stageName}`,
  required_inputs: [],
  optional_inputs: [],
  expected_outputs: [],
  artifact_types: [],
  validators: [],
  approval_gates: [],
  checkpoint_policy: "on_completion",
  recovery_policy: "restart"
};

fs.writeFileSync(stageFile, JSON.stringify(template, null, 2));

console.log(`Stage created: ${stageName}`);
console.log(`  File: ${stageFile}`);
