#!/usr/bin/env node
/**
 * Run all schema validation tests.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const childProcess = require('child_process');
const Ajv = require('ajv');

const ROOT = path.resolve(__dirname, '../..');
const SCHEMAS_DIR = path.join(ROOT, 'schemas');
const FIXTURES_DIR = path.join(ROOT, 'tests/fixtures');

let passed = 0;
let failed = 0;

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relativePath), 'utf-8'));
}

function compileSchema(name) {
  const ajv = new Ajv({ strict: false, validateFormats: false });
  return ajv.compile(readJson(path.join('schemas', name)));
}

function buildRuntimeFixtures() {
  const timestamp = '2026-07-11T00:00:00+00:00';
  const workflow = {
    workflow_id: 'wf_ab12cd34',
    workflow_type: 'custom_recipe',
    current_stage: 'literature_review',
    status: 'initialized',
    plan: null,
    entry_point: 'literature_review',
    created_at: timestamp,
    updated_at: timestamp,
  };
  const stage = {
    stage_name: 'literature_review',
    status: 'completed',
    agent: null,
    inputs: ['seed'],
    outputs: ['art_1234abcd'],
    checkpoint_id: 'ckpt_001_literature_review',
    error_message: null,
    started_at: timestamp,
    completed_at: timestamp,
  };
  const artifact = {
    artifact_id: 'art_1234abcd',
    name: 'summary.txt',
    type: 'review_summary',
    version: 'v1.0.0',
    stage: 'literature_review',
    path: '.simflow/artifacts/literature_review/summary.txt',
    lineage: {
      parent_artifacts: [],
      parameters: {},
      software: null,
    },
    metadata: {},
    checksum: null,
    created_at: timestamp,
  };
  const checkpoint = {
    checkpoint_id: 'ckpt_001_literature_review',
    workflow_id: workflow.workflow_id,
    stage_id: 'literature_review',
    job_id: null,
    description: 'Checkpoint after literature review',
    state_snapshot: {
      'workflow.json': workflow,
      'stages.json': { literature_review: stage },
      'artifacts.json': [artifact],
      'checkpoints.json': [{
        checkpoint_id: 'ckpt_001_literature_review',
        workflow_id: workflow.workflow_id,
        stage_id: 'literature_review',
        job_id: null,
        description: 'Checkpoint after literature review',
        status: 'success',
        path: '.simflow/checkpoints/ckpt_001_literature_review.json',
        created_at: timestamp,
      }],
      'lineage.json': { links: [] },
      'verification.json': [],
      'jobs.json': [],
      'gates.json': [],
      'metadata.json': {},
      'summary.json': { state_root: '.simflow' },
      'project.json': {
        project_root: '/tmp/project',
        state_root: '.simflow',
        workflow_id: workflow.workflow_id,
        created_at: timestamp,
        updated_at: timestamp,
      },
    },
    artifact_versions: {
      art_1234abcd: 'v1.0.0',
    },
    lineage_snapshot: { links: [] },
    status: 'success',
    created_at: timestamp,
    simflow_result: {
      schema_version: 'simflow.result.v1',
      role: 'state_admin',
      activity: 'create_checkpoint',
      legacy_status: 'success',
      outcome: 'success',
      stage: 'literature_review',
      state_effect: 'checkpoint_admin',
    },
  };
  const verification = [{
    stage: 'writing',
    workflow_id: workflow.workflow_id,
    status: 'pass',
    generated_at: timestamp,
    completed_at: timestamp,
    checks: [{
      name: 'traceability',
      status: 'pass',
      message: 'ok',
      details: {},
      checked_at: timestamp,
    }],
    warnings: [],
    failures: [],
    source_artifact_ids: [],
  }];
  return {
    workflow,
    stages: { literature_review: stage },
    artifacts: [artifact],
    checkpoints: checkpoint.state_snapshot['checkpoints.json'],
    verification,
    artifact,
    checkpoint,
  };
}

function buildActualRuntimeState() {
  const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'simflow-schema-'));
  const script = `
from pathlib import Path
import json
import sys

root = Path(sys.argv[1])
repo_root = Path(sys.argv[2])
sys.path.insert(0, str(repo_root / "runtime"))

from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint
from runtime.simflow_core.state import CANONICAL_STATE_FILES, init_workflow, read_state, update_stage

workflow = init_workflow("custom_recipe", "literature_review", project_root=str(root))
initialized = {
    "artifacts": read_state(project_root=str(root), state_file="artifacts.json"),
    "checkpoints": read_state(project_root=str(root), state_file="checkpoints.json"),
    "jobs": read_state(project_root=str(root), state_file="jobs.json"),
    "gates": read_state(project_root=str(root), state_file="gates.json"),
    "verification": read_state(project_root=str(root), state_file="verification.json"),
}
canonical = {
    name: read_state(project_root=str(root), state_file=name)
    for name in CANONICAL_STATE_FILES
}
artifact_path = root / "literature" / "summary.txt"
artifact_path.parent.mkdir(parents=True, exist_ok=True)
artifact_path.write_text("summary\\n", encoding="utf-8")
update_stage(
    "literature_review",
    "completed",
    project_root=str(root),
    inputs=["seed"],
    outputs=["art_1234abcd"],
)
artifact = register_artifact(
    "summary.txt",
    "review_summary",
    "literature_review",
    path="literature/summary.txt",
    project_root=str(root),
)
checkpoint = create_checkpoint(
    workflow["workflow_id"],
    "literature_review",
    "Checkpoint after literature review",
    project_root=str(root),
)
produced = {
    "workflow": read_state(project_root=str(root), state_file="workflow.json"),
    "stages": read_state(project_root=str(root), state_file="stages.json"),
    "artifacts": read_state(project_root=str(root), state_file="artifacts.json"),
    "checkpoints": read_state(project_root=str(root), state_file="checkpoints.json"),
    "artifact": artifact,
    "checkpoint": checkpoint,
}
print(json.dumps({"initialized": initialized, "canonical": canonical, "produced": produced}))
`;
  const result = childProcess.spawnSync('python', ['-c', script, projectRoot, ROOT], {
    cwd: ROOT,
    encoding: 'utf-8',
  });
  try {
    if (result.status !== 0) {
      throw new Error(result.stderr || result.stdout || 'python helper failed');
    }
    return JSON.parse(result.stdout);
  } finally {
    fs.rmSync(projectRoot, { recursive: true, force: true });
  }
}

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

test('runtime-produced workflow, stage, artifact, checkpoint, and verification state validate against schemas', () => {
  const fixtures = buildRuntimeFixtures();
  const stateSchema = compileSchema('state.schema.json');
  const workflowSchema = compileSchema('workflow_state.json');
  const stageSchema = compileSchema('stage_state.json');
  const artifactSchema = compileSchema('artifact.json');
  const checkpointSchema = compileSchema('checkpoint.json');
  const verificationSchema = compileSchema('verification.json');

  if (!stateSchema(fixtures.workflow)) {
    throw new Error(`workflow.json rejected: ${JSON.stringify(stateSchema.errors)}`);
  }
  if (!stateSchema(fixtures.stages)) {
    throw new Error(`stages.json rejected: ${JSON.stringify(stateSchema.errors)}`);
  }
  if (!stateSchema(fixtures.artifacts)) {
    throw new Error(`artifacts.json rejected: ${JSON.stringify(stateSchema.errors)}`);
  }
  if (!stateSchema(fixtures.checkpoints)) {
    throw new Error(`checkpoints.json rejected: ${JSON.stringify(stateSchema.errors)}`);
  }
  if (!stateSchema(fixtures.verification)) {
    throw new Error(`verification.json rejected: ${JSON.stringify(stateSchema.errors)}`);
  }
  if (!workflowSchema(fixtures.workflow)) {
    throw new Error(`workflow_state.json rejected: ${JSON.stringify(workflowSchema.errors)}`);
  }
  if (!stageSchema(fixtures.stages.literature_review)) {
    throw new Error(`stage_state.json rejected: ${JSON.stringify(stageSchema.errors)}`);
  }
  if (!artifactSchema(fixtures.artifact)) {
    throw new Error(`artifact.json rejected: ${JSON.stringify(artifactSchema.errors)}`);
  }
  if (!checkpointSchema(fixtures.checkpoint)) {
    throw new Error(`checkpoint.json rejected: ${JSON.stringify(checkpointSchema.errors)}`);
  }
  if (!verificationSchema(fixtures.verification[0])) {
    throw new Error(`verification.json component rejected: ${JSON.stringify(verificationSchema.errors)}`);
  }
});

test('actual init_workflow empty array states validate against the unified schema', () => {
  const runtimeState = buildActualRuntimeState();
  const stateSchema = compileSchema('state.schema.json');

  ['artifacts', 'checkpoints', 'jobs', 'gates', 'verification'].forEach((name) => {
    if (!stateSchema(runtimeState.initialized[name])) {
      throw new Error(`${name}.json rejected: ${JSON.stringify(stateSchema.errors)}`);
    }
  });
});

test('actual init_workflow canonical state files validate by file name', () => {
  const runtimeState = buildActualRuntimeState();
  const stateSchema = compileSchema('state.schema.json');
  const expected = [
    'project.json',
    'workflow.json',
    'stages.json',
    'artifacts.json',
    'checkpoints.json',
    'gates.json',
    'lineage.json',
    'verification.json',
    'jobs.json',
    'summary.json',
    'metadata.json',
  ];
  const actual = Object.keys(runtimeState.canonical).sort();
  const missing = expected.filter((name) => !actual.includes(name));
  if (missing.length) {
    throw new Error(`missing canonical state files: ${missing.join(', ')}`);
  }
  expected.forEach((name) => {
    if (!stateSchema(runtimeState.canonical[name])) {
      throw new Error(`${name} rejected: ${JSON.stringify(stateSchema.errors)}`);
    }
  });
  const metadata = {
    research_goal: 'screen lanthanide hydration structures',
    labels: ['dft', 'vasp'],
    project_notes: { owner: 'local', pii_free: true },
  };
  if (!stateSchema(metadata)) {
    throw new Error(`metadata.json project-specific object rejected: ${JSON.stringify(stateSchema.errors)}`);
  }
});

test('actual runtime-produced workflow, stages, artifact, and checkpoint records validate against schemas', () => {
  const runtimeState = buildActualRuntimeState();
  const stateSchema = compileSchema('state.schema.json');
  const workflowSchema = compileSchema('workflow_state.json');
  const stageSchema = compileSchema('stage_state.json');
  const artifactSchema = compileSchema('artifact.json');
  const checkpointSchema = compileSchema('checkpoint.json');

  if (!stateSchema(runtimeState.produced.workflow)) {
    throw new Error(`workflow.json rejected: ${JSON.stringify(stateSchema.errors)}`);
  }
  if (!stateSchema(runtimeState.produced.stages)) {
    throw new Error(`stages.json rejected: ${JSON.stringify(stateSchema.errors)}`);
  }
  if (!stateSchema(runtimeState.produced.artifacts)) {
    throw new Error(`artifacts.json rejected: ${JSON.stringify(stateSchema.errors)}`);
  }
  if (!stateSchema(runtimeState.produced.checkpoints)) {
    throw new Error(`checkpoints.json rejected: ${JSON.stringify(stateSchema.errors)}`);
  }
  if (!workflowSchema(runtimeState.produced.workflow)) {
    throw new Error(`workflow_state.json rejected: ${JSON.stringify(workflowSchema.errors)}`);
  }
  if (!stageSchema(runtimeState.produced.stages.literature_review)) {
    throw new Error(`stage_state.json rejected: ${JSON.stringify(stageSchema.errors)}`);
  }
  if (!artifactSchema(runtimeState.produced.artifact)) {
    throw new Error(`artifact.json rejected: ${JSON.stringify(artifactSchema.errors)}`);
  }
  if (!checkpointSchema(runtimeState.produced.checkpoint)) {
    throw new Error(`checkpoint.json rejected: ${JSON.stringify(checkpointSchema.errors)}`);
  }
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
  if (!contract.helper_supported_software.includes('gpumd') || !contract.helper_supported_software.includes('nep')) {
    throw new Error('GPUMD/NEP must be helper_supported');
  }
  ['real_execution', 'local_submit', 'remote_execution', 'hpc_submit'].forEach(capability => {
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
  if (!contract.policy.includes('never execute tools')) {
    throw new Error('Adapter policy must reject execution semantics');
  }
  const active = contract.adapters.filter(adapter => adapter.runtime_enabled).map(adapter => adapter.tool_id);
  if (active.join(',') !== 'lammps,gpumd,nep') {
    throw new Error(`Unexpected active adapters: ${active.join(',')}`);
  }
});

test('adapter_enablement_review.schema.json defines candidate-only expansion gate', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'adapter_enablement_review.schema.json'), 'utf-8'));
  ['schema_version', 'policy', 'reviews'].forEach(field => {
    if (!schema.required || !schema.required.includes(field)) {
      throw new Error(`Missing required adapter enablement review field: ${field}`);
    }
  });
  const contract = JSON.parse(fs.readFileSync(path.join(ROOT, 'workflow', 'toolchains', 'adapter_enablement_reviews.json'), 'utf-8'));
  if (contract.schema_version !== 'simflow.adapter_enablement_reviews.v1') {
    throw new Error('Unexpected adapter enablement review schema version');
  }
  if (!contract.policy.includes('does not execute tools')) {
    throw new Error('Adapter enablement policy must reject execution semantics');
  }
  const reviewTools = contract.reviews.map(review => review.tool_id);
  ['deepmd', 'mace', 'nequip', 'allegro', 'gromacs', 'quantum_espresso'].forEach(tool => {
    if (!reviewTools.includes(tool)) {
      throw new Error(`Missing candidate review for ${tool}`);
    }
  });
  const activeRequests = contract.reviews.filter(review => review.requested_runtime_enabled);
  if (activeRequests.length !== 0) {
    throw new Error('Stage3 candidate reviews must not request runtime enablement');
  }
});

test('helper_evidence.schema.json defines common soft evidence envelope', () => {
  const schema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'helper_evidence.schema.json'), 'utf-8'));
  ['schema_version', 'helper', 'capability', 'status', 'stage', 'activity', 'evidence_role'].forEach(field => {
    if (!schema.required || !schema.required.includes(field)) {
      throw new Error(`Missing required helper evidence field: ${field}`);
    }
  });
  const statuses = schema.properties.status.enum || [];
  ['success', 'warning', 'blocked', 'incomplete', 'skipped_optional_dependency', 'capability_warning'].forEach(status => {
    if (!statuses.includes(status)) {
      throw new Error(`Missing helper evidence status: ${status}`);
    }
  });
  const parserStatuses = schema.properties.parser_status.enum || [];
  ['parsed', 'partial', 'unrecognized', 'missing', 'malformed', 'not_applicable'].forEach(status => {
    if (!parserStatuses.includes(status)) {
      throw new Error(`Missing parser status: ${status}`);
    }
  });
});

test('skill-contract.schema.json supports built-in and custom skill frontmatter', () => {
  const validate = compileSchema('skill-contract.schema.json');
  const builtin = {
    skill_name: 'simflow-computation',
    description: 'Prepare, validate, dry-run, or submit simulation jobs.',
    stage_binding: ['computation'],
  };
  const custom = {
    skill_name: 'my-custom-analysis:run_analysis',
    description: 'Project-local RDF analysis helper.',
    stage_binding: 'analysis',
  };
  if (!validate(builtin)) {
    throw new Error(`Built-in skill contract rejected: ${JSON.stringify(validate.errors)}`);
  }
  if (!validate(custom)) {
    throw new Error(`Custom skill contract rejected: ${JSON.stringify(validate.errors)}`);
  }
});

test('custom-skill-metadata.schema.json permits project-local activity labels', () => {
  const validate = compileSchema('custom-skill-metadata.schema.json');
  const metadata = {
    name: 'my-custom-analysis',
    version: '1.0.0',
    description: 'Custom RDF analysis with publication-quality plots',
    author: 'researcher@university.edu',
    stage_binding: 'analysis',
  };
  if (!validate(metadata)) {
    throw new Error(`Custom metadata rejected: ${JSON.stringify(validate.errors)}`);
  }
});

test('custom-skill-binding.schema.json remains scoped to built-in SimFlow skill overrides', () => {
  const validate = compileSchema('custom-skill-binding.schema.json');
  const binding = {
    skill_name: 'simflow-computation',
    binding_type: 'extend',
    extends: {
      additional_scripts: ['scripts/custom_submit_readiness.py'],
    },
  };
  const metadataShape = {
    name: 'my-custom-analysis',
    version: '1.0.0',
    description: 'Custom RDF analysis',
    stage_binding: 'analysis',
  };
  if (!validate(binding)) {
    throw new Error(`Built-in binding rejected: ${JSON.stringify(validate.errors)}`);
  }
  if (validate(metadataShape)) {
    throw new Error('Custom skill metadata must not validate as an override binding');
  }
});

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===`);
process.exit(failed > 0 ? 1 : 0);
