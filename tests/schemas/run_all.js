#!/usr/bin/env node
/**
 * Run all schema validation tests.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const SCHEMAS_DIR = path.join(ROOT, 'schemas');
const FIXTURES_DIR = path.join(ROOT, 'tests/fixtures');

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  PASS: ${name}`);
    passed++;
  } catch (e) {
    console.error(`  FAIL: ${name} - ${e.message}`);
    failed++;
  }
}

console.log('=== Schema Tests ===\n');

// Test schemas are valid JSON
test('All schema files are valid JSON', () => {
  const files = fs.readdirSync(SCHEMAS_DIR).filter(f => f.endsWith('.json'));
  if (files.length === 0) throw new Error('No schema files found');
  files.forEach(f => {
    JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, f), 'utf-8'));
  });
});

// Test workflow_state schema
test('workflow_state.json has required fields', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'workflow_state.json'), 'utf-8'));
  const required = ['workflow_id', 'workflow_type', 'current_stage', 'status'];
  required.forEach(f => {
    if (!schema.required || !schema.required.includes(f)) {
      throw new Error(`Missing required field: ${f}`);
    }
  });
});

// Test artifact schema
test('artifact.json has lineage support', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'artifact.json'), 'utf-8'));
  if (!schema.properties.lineage) throw new Error('Missing lineage property');
});

// Test checkpoint schema
test('checkpoint.json has workflow_id and stage_id', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'checkpoint.json'), 'utf-8'));
  const required = ['checkpoint_id', 'workflow_id', 'stage_id'];
  required.forEach(f => {
    if (!schema.required || !schema.required.includes(f)) {
      throw new Error(`Missing required field: ${f}`);
    }
  });
});

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===`);
process.exit(failed > 0 ? 1 : 0);
