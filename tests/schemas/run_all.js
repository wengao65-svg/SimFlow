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

test('workflow.schema.json keeps workflow_type open', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'workflow.schema.json'), 'utf-8'));
  const workflowType = schema.properties && schema.properties.workflow_type;
  if (!workflowType) throw new Error('Missing workflow_type property');
  if (workflowType.enum) throw new Error('workflow_type must not be enum-limited');
  ['recipe', 'tags', 'software'].forEach(field => {
    if (!schema.properties[field]) throw new Error(`Missing open workflow field: ${field}`);
  });
});

test('workflow.schema.json allows string or object stages', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'workflow.schema.json'), 'utf-8'));
  const oneOf = schema.properties.stages.items.oneOf || [];
  const types = new Set(oneOf.map(item => item.type));
  if (!types.has('string') || !types.has('object')) {
    throw new Error('stages items must allow both string and object entries');
  }
});

test('stage.schema.json requires intent and evidence_outputs', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'stage.schema.json'), 'utf-8'));
  ['name', 'intent', 'evidence_outputs'].forEach(field => {
    if (!schema.required || !schema.required.includes(field)) {
      throw new Error(`Missing required stage field: ${field}`);
    }
  });
  ['skill', 'inputs', 'outputs', 'default_skill', 'required_inputs', 'expected_outputs'].forEach(field => {
    if (schema.required && schema.required.includes(field)) {
      throw new Error(`Legacy field must not be required: ${field}`);
    }
  });
});

test('stage.schema.json includes guidance and approval fields', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'stage.schema.json'), 'utf-8'));
  ['acceptable_inputs', 'recommended_skills', 'suggested_checks', 'approval_triggers', 'handoff_notes'].forEach(field => {
    if (!schema.properties[field]) throw new Error(`Missing stage guidance field: ${field}`);
  });
});

test('recipe.schema.json defines open JSON recipe contract', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'recipe.schema.json'), 'utf-8'));
  ['name', 'recipe_type', 'intent', 'stages'].forEach(field => {
    if (!schema.required || !schema.required.includes(field)) {
      throw new Error(`Missing required recipe field: ${field}`);
    }
  });
  if (schema.properties.recipe_type.enum) {
    throw new Error('recipe_type must remain open and not enum-limited');
  }
  ['applicable_software', 'evidence_outputs', 'recommended_checks', 'approval_triggers'].forEach(field => {
    if (!schema.properties[field]) throw new Error(`Missing recipe guidance field: ${field}`);
  });
});

test('toolchain_capabilities.schema.json defines non-executor capability contract', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'toolchain_capabilities.schema.json'), 'utf-8'));
  ['schema_version', 'policy', 'helper_supported_software', 'tracked_only_software', 'aliases', 'capability_support'].forEach(field => {
    if (!schema.required || !schema.required.includes(field)) {
      throw new Error(`Missing required toolchain capability field: ${field}`);
    }
  });
  const contract = JSON.parse(fs.readFileSync(path.join(ROOT, 'workflow', 'toolchains', 'capabilities.json'), 'utf-8'));
  if (contract.schema_version !== 'simflow.toolchain_capabilities.v1') {
    throw new Error('Unexpected toolchain capability schema version');
  }
  if (!contract.policy.includes('not define software admission')) {
    throw new Error('Capability contract policy must reject admission-registry semantics');
  }
  if (!contract.tracked_only_software.includes('gpumd') || !contract.tracked_only_software.includes('nep')) {
    throw new Error('GPUMD/NEP must remain tracked_only');
  }
  ['input_generation', 'real_execution', 'local_submit', 'remote_execution', 'hpc_submit'].forEach(capability => {
    if (!contract.capability_support.gpumd.not_helper_supported.includes(capability)) {
      throw new Error(`GPUMD must block helper support for ${capability}`);
    }
    if (!contract.capability_support.nep.not_helper_supported.includes(capability)) {
      throw new Error(`NEP must block helper support for ${capability}`);
    }
  });
});

test('helper_adapter.schema.json defines metadata-only active adapter contract', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'helper_adapter.schema.json'), 'utf-8'));
  ['schema_version', 'policy', 'adapters'].forEach(field => {
    if (!schema.required || !schema.required.includes(field)) {
      throw new Error(`Missing required helper adapter field: ${field}`);
    }
  });
  const contract = JSON.parse(fs.readFileSync(path.join(ROOT, 'workflow', 'toolchains', 'adapters.json'), 'utf-8'));
  if (contract.schema_version !== 'simflow.helper_adapters.v1') {
    throw new Error('Unexpected helper adapter schema version');
  }
  if (!contract.policy.includes('do not execute tools')) {
    throw new Error('Adapter policy must reject execution semantics');
  }
  const active = contract.adapters.filter(adapter => adapter.runtime_enabled).map(adapter => adapter.tool_id);
  if (active.join(',') !== 'lammps,gpumd,nep') {
    throw new Error(`Unexpected active adapters: ${active.join(',')}`);
  }
});

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===`);
process.exit(failed > 0 ? 1 : 0);
