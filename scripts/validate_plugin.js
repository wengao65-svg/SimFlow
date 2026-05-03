#!/usr/bin/env node
/**
 * Validate the SimFlow plugin structure.
 * Checks that all required files and directories exist.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

const REQUIRED_FILES = [
  '.codex-plugin/plugin.json',
  '.codex/config.toml',
  '.codex/hooks.json',
  'AGENTS.md',
  'package.json',
  'README.md',
];

const REQUIRED_DIRS = [
  'skills',
  'agents',
  'workflow/stages',
  'workflow/workflows',
  'workflow/gates',
  'workflow/policies',
  'mcp/servers',
  'runtime/lib',
  'runtime/scripts',
  'schemas',
  'hooks',
  'notifications',
  'templates',
];

const REQUIRED_STAGES = [
  'literature', 'review', 'proposal', 'modeling',
  'input_generation', 'compute', 'analysis', 'visualization', 'writing',
];

const REQUIRED_WORKFLOWS = ['dft', 'aimd', 'md'];

let errors = 0;
let warnings = 0;

function check(label, condition, isWarning = false) {
  if (!condition) {
    if (isWarning) {
      console.warn(`  WARNING: ${label}`);
      warnings++;
    } else {
      console.error(`  ERROR: ${label}`);
      errors++;
    }
  } else {
    console.log(`  OK: ${label}`);
  }
}

console.log('=== SimFlow Plugin Validation ===\n');

// Check required files
console.log('--- Required Files ---');
REQUIRED_FILES.forEach(f => {
  check(f, fs.existsSync(path.join(ROOT, f)));
});

// Check required directories
console.log('\n--- Required Directories ---');
REQUIRED_DIRS.forEach(d => {
  check(d, fs.existsSync(path.join(ROOT, d)));
});

// Check plugin.json
console.log('\n--- Plugin Configuration ---');
try {
  const plugin = JSON.parse(fs.readFileSync(path.join(ROOT, '.codex-plugin/plugin.json'), 'utf-8'));
  check('plugin.json has name', !!plugin.name);
  check('plugin.json has version', !!plugin.version);
  check('plugin.json has entry_points', !!plugin.entry_points);
} catch (e) {
  check('plugin.json is valid JSON', false);
}

// Check stage definitions
console.log('\n--- Stage Definitions ---');
REQUIRED_STAGES.forEach(s => {
  check(`stages/${s}.json`, fs.existsSync(path.join(ROOT, 'workflow/stages', `${s}.json`)));
});

// Check workflow definitions
console.log('\n--- Workflow Definitions ---');
REQUIRED_WORKFLOWS.forEach(w => {
  check(`workflows/${w}.json`, fs.existsSync(path.join(ROOT, 'workflow/workflows', `${w}.json`)));
});

// Check skills
console.log('\n--- Skills ---');
const skillsDir = path.join(ROOT, 'skills');
if (fs.existsSync(skillsDir)) {
  const skills = fs.readdirSync(skillsDir).filter(d =>
    fs.existsSync(path.join(skillsDir, d, 'SKILL.md'))
  );
  check(`At least 10 skills found`, skills.length >= 10);
  console.log(`  Found ${skills.length} skills`);
} else {
  check('skills directory exists', false);
}

// Check schemas
console.log('\n--- Schemas ---');
const schemasDir = path.join(ROOT, 'schemas');
if (fs.existsSync(schemasDir)) {
  const schemas = fs.readdirSync(schemasDir).filter(f => f.endsWith('.json'));
  check(`At least 4 schemas found`, schemas.length >= 4);
  console.log(`  Found ${schemas.length} schemas`);
}

// Summary
console.log('\n=== Summary ===');
console.log(`Errors: ${errors}`);
console.log(`Warnings: ${warnings}`);
process.exit(errors > 0 ? 1 : 0);
