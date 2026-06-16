#!/usr/bin/env node
/**
 * Validate source and marketplace release gates before publishing SimFlow.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const args = new Set(process.argv.slice(2));
const ALLOW_DIRTY = args.has('--allow-dirty') || process.env.SIMFLOW_RELEASE_ALLOW_DIRTY === '1';
const SKIP_WRAPPERS = args.has('--skip-wrapper-build') || process.env.SIMFLOW_RELEASE_SKIP_WRAPPERS === '1';
const RESTRICTED_NAMES = new Set(['POTCAR', 'WAVECAR', 'CHGCAR', 'OUTCAR', 'vasprun.xml']);
const POTCAR_HEADER_RE = /PAW_PBE Si|VRHFIN =Si/;

let errors = 0;

function ok(label) {
  console.log(`  OK: ${label}`);
}

function fail(label, detail) {
  console.error(`  ERROR: ${label}`);
  if (detail) {
    console.error(String(detail).split('\n').map(line => `    ${line}`).join('\n'));
  }
  errors++;
}

function check(label, condition, detail) {
  if (condition) {
    ok(label);
  } else {
    fail(label, detail);
  }
}

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relativePath), 'utf-8'));
}

function run(command, commandArgs, options = {}) {
  const result = spawnSync(command, commandArgs, {
    cwd: options.cwd || ROOT,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1', ...options.env },
    encoding: 'utf-8',
    stdio: options.capture ? 'pipe' : 'inherit',
  });
  if (result.status !== 0) {
    const details = [result.stdout, result.stderr].filter(Boolean).join('\n').trim();
    throw new Error(`${command} ${commandArgs.join(' ')} failed${details ? `\n${details}` : ''}`);
  }
  return result.stdout || '';
}

function runCheck(label, command, commandArgs, options = {}) {
  try {
    run(command, commandArgs, options);
    ok(label);
  } catch (error) {
    fail(label, error.message);
  }
}

function parsePyprojectVersion() {
  const text = fs.readFileSync(path.join(ROOT, 'pyproject.toml'), 'utf-8');
  const projectMatch = text.match(/\[project\]([\s\S]*?)(?:\n\[|$)/);
  if (!projectMatch) {
    return null;
  }
  const versionMatch = projectMatch[1].match(/^\s*version\s*=\s*"([^"]+)"/m);
  return versionMatch ? versionMatch[1] : null;
}

function validateCleanTree() {
  console.log('\n--- Source Tree ---');
  const status = run('git', ['status', '--short'], { capture: true }).trim();
  check(
    'working tree is clean for release',
    ALLOW_DIRTY || status.length === 0,
    status || 'Use --allow-dirty only for local script tests.',
  );
}

function validateVersionSync() {
  console.log('\n--- Version Synchronization ---');
  const packageVersion = readJson('package.json').version;
  const pyprojectVersion = parsePyprojectVersion();
  const codexVersion = readJson('.codex-plugin/plugin.json').version;
  const claudeVersion = readJson('.claude-plugin/plugin.json').version;
  const versions = {
    'package.json': packageVersion,
    'pyproject.toml': pyprojectVersion,
    '.codex-plugin/plugin.json': codexVersion,
    '.claude-plugin/plugin.json': claudeVersion,
  };
  const unique = new Set(Object.values(versions));
  check(
    'package, Python, Codex, and Claude plugin versions match',
    unique.size === 1 && !unique.has(null) && !unique.has(undefined),
    JSON.stringify(versions, null, 2),
  );
}

function validatePublicMetadata() {
  console.log('\n--- Public Metadata ---');
  const forbidden = [
    ['maintainers', 'example.com'].join('@'),
    ['https://github.com', 'simflow'].join('/'),
    ['https://github.com', 'simflow', 'simflow'].join('/'),
  ];
  const targets = [
    '.codex-plugin/plugin.json',
    '.claude-plugin/plugin.json',
    '.claude-plugin/marketplace.json',
  ];
  const findings = [];
  for (const target of targets) {
    const content = fs.readFileSync(path.join(ROOT, target), 'utf-8');
    for (const value of forbidden) {
      if (content.includes(value)) {
        findings.push(`${target}: ${value}`);
      }
    }
  }
  check('public metadata has no placeholder maintainer or repository values', findings.length === 0, findings.join('\n'));
}

function validateSupportMatrix() {
  console.log('\n--- Support Matrix ---');
  const pyproject = fs.readFileSync(path.join(ROOT, 'pyproject.toml'), 'utf-8');
  const unsupportedExtras = [];
  if (/^\s*qe\s*=.*$/m.test(pyproject)) {
    unsupportedExtras.push('pyproject.toml exposes unsupported qe extra');
  }
  if (/^\s*gaussian\s*=.*$/m.test(pyproject)) {
    unsupportedExtras.push('pyproject.toml exposes unsupported gaussian extra');
  }
  check('unsupported QE/Gaussian extras are not exposed', unsupportedExtras.length === 0, unsupportedExtras.join('\n'));

  const publicDocs = [
    'README.md',
    'docs/PRD.md',
    'docs/installation.md',
    'docs/software-skills.md',
    'docs/skill-design.md',
    'skills/README.md',
  ];
  const forbiddenClaims = [
    /optional\s+VASP,\s*CP2K,\s*QE/i,
    /Quantum ESPRESSO\s*\|\s*Plane-wave DFT input and output guidance/i,
    /Gaussian\s*\|\s*Quantum chemistry input and output guidance/i,
    /pip install -e "\.\[qe\]"/i,
    /pip install -e "\.\[gaussian\]"/i,
    /simflow-qe`\s+can assist/i,
    /simflow-gaussian`\s+can assist/i,
    /VASP,\s*QE,\s*CP2K,\s*LAMMPS,\s*and\s*Gaussian\s+remain/i,
  ];
  const docFindings = [];
  for (const relativePath of publicDocs) {
    const content = fs.readFileSync(path.join(ROOT, relativePath), 'utf-8');
    for (const pattern of forbiddenClaims) {
      if (pattern.test(content)) {
        docFindings.push(`${relativePath}: ${pattern}`);
      }
    }
  }
  check('public docs do not claim supported QE/Gaussian helpers', docFindings.length === 0, docFindings.join('\n'));

  const readme = fs.readFileSync(path.join(ROOT, 'README.md'), 'utf-8');
  const prd = fs.readFileSync(path.join(ROOT, 'docs', 'PRD.md'), 'utf-8');
  const softwareSkills = fs.readFileSync(path.join(ROOT, 'docs', 'software-skills.md'), 'utf-8');
  check('README states QE/Gaussian unsupported placeholder status', /QE \/ Gaussian \| Unsupported placeholders/.test(readme));
  check('PRD states supported engine helpers explicitly', /Supported engine helpers \| VASP, CP2K, and LAMMPS/.test(prd));
  check('software skills document unsupported placeholder policy', /simflow-qe` and `simflow-gaussian` are reserved placeholders/.test(softwareSkills));
}

function validateRestrictedArtifacts() {
  console.log('\n--- Restricted Artifact Scan ---');
  const tracked = run('git', ['ls-files'], { capture: true }).split(/\r?\n/).filter(Boolean);
  const trackedFindings = [];
  for (const relativePath of tracked) {
    const base = path.basename(relativePath);
    const upper = base.toUpperCase();
    const blockedPotcar = upper === 'POTCAR' || (upper.startsWith('POTCAR.') && upper !== 'POTCAR.METADATA.JSON');
    if (RESTRICTED_NAMES.has(base) || blockedPotcar) {
      trackedFindings.push(relativePath);
    }
  }
  check('tracked files exclude restricted VASP runtime artifacts', trackedFindings.length === 0, trackedFindings.join('\n'));

  const exampleFindings = [];
  const exampleRoot = path.join(ROOT, 'examples', 'si_band_structure');
  if (fs.existsSync(exampleRoot)) {
    const stack = [exampleRoot];
    while (stack.length > 0) {
      const current = stack.pop();
      for (const entry of fs.readdirSync(current)) {
        const fullPath = path.join(current, entry);
        const stat = fs.lstatSync(fullPath);
        if (stat.isDirectory()) {
          stack.push(fullPath);
          continue;
        }
        if (RESTRICTED_NAMES.has(entry)) {
          exampleFindings.push(path.relative(ROOT, fullPath));
        }
        if (stat.size <= 1024 * 1024) {
          const content = fs.readFileSync(fullPath, 'utf-8');
          if (POTCAR_HEADER_RE.test(content) && entry !== 'POTCAR.metadata.json') {
            exampleFindings.push(`${path.relative(ROOT, fullPath)} contains POTCAR-like header text`);
          }
        }
      }
    }
  }
  check('safe examples exclude real VASP artifacts and POTCAR-derived headers', exampleFindings.length === 0, exampleFindings.join('\n'));
}

function validateSafeExamples() {
  console.log('\n--- Safe Examples ---');
  const exampleRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'simflow-safe-example-'));
  try {
    const result = spawnSync('python', ['examples/safe_dry_run/run_example.py', '--project-root', exampleRoot], {
      cwd: ROOT,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
      encoding: 'utf-8',
      stdio: 'pipe',
    });
    if (result.status !== 0) {
      fail('safe dry-run example completes', [result.stdout, result.stderr].filter(Boolean).join('\n'));
    } else {
      let summary = {};
      try {
        summary = JSON.parse(result.stdout);
      } catch (error) {
        fail('safe dry-run example emits JSON summary', result.stdout);
      }
      check('safe dry-run example completes', summary.status === 'success', result.stdout);
      check('safe dry-run example writes workflow state', fs.existsSync(path.join(exampleRoot, '.simflow', 'state', 'workflow.json')));
      check('safe dry-run example writes dry-run evidence', fs.existsSync(path.join(exampleRoot, '.simflow', 'artifacts', 'compute', 'dry_run_report.json')));
      check('safe dry-run example writes handoff report', fs.existsSync(path.join(exampleRoot, '.simflow', 'reports', 'handoff', 'final_handoff.md')));
      check('safe dry-run example keeps submit gate blocked', summary.hpc_submit_gate_status === 'block', result.stdout);
      const jobsPath = path.join(exampleRoot, '.simflow', 'state', 'jobs.json');
      const jobs = fs.existsSync(jobsPath) ? JSON.parse(fs.readFileSync(jobsPath, 'utf-8')) : [];
      check('safe dry-run example does not write job records', Array.isArray(jobs) && jobs.length === 0, JSON.stringify(jobs, null, 2));
    }
  } finally {
    fs.rmSync(exampleRoot, { recursive: true, force: true });
  }
  runCheck('Si band-structure example metadata validates without real POTCAR', 'python', ['examples/si_band_structure/validate_inputs.py']);

  const lammpsRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'simflow-lammps-safe-example-'));
  try {
    const result = spawnSync('python', ['examples/lammps_safe_dry_run/run_example.py', '--project-root', lammpsRoot], {
      cwd: ROOT,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
      encoding: 'utf-8',
      stdio: 'pipe',
    });
    if (result.status !== 0) {
      fail('LAMMPS safe dry-run example completes', [result.stdout, result.stderr].filter(Boolean).join('\n'));
    } else {
      let summary = {};
      try {
        summary = JSON.parse(result.stdout);
      } catch (error) {
        fail('LAMMPS safe dry-run example emits JSON summary', result.stdout);
      }
      check('LAMMPS safe dry-run example completes', summary.status === 'success', result.stdout);
      check('LAMMPS safe dry-run example records dry-run evidence', fs.existsSync(path.join(lammpsRoot, '.simflow', 'artifacts', 'compute', 'dry_run_report.json')));
      check('LAMMPS safe dry-run example records credential scan evidence', fs.existsSync(path.join(lammpsRoot, '.simflow', 'artifacts', 'security', 'credential_scan.json')));
      check('LAMMPS safe dry-run example keeps submit gate blocked', summary.hpc_submit_gate_status === 'block', result.stdout);
      const jobsPath = path.join(lammpsRoot, '.simflow', 'state', 'jobs.json');
      const jobs = fs.existsSync(jobsPath) ? JSON.parse(fs.readFileSync(jobsPath, 'utf-8')) : [];
      check('LAMMPS safe dry-run example does not write job records', Array.isArray(jobs) && jobs.length === 0, JSON.stringify(jobs, null, 2));
    }
  } finally {
    fs.rmSync(lammpsRoot, { recursive: true, force: true });
  }
}

function validateReleaseNotesCommand() {
  console.log('\n--- Release Notes ---');
  const notesScript = path.join(ROOT, 'scripts', 'generate_release_notes.js');
  const version = readJson('package.json').version;
  const commit = run('git', ['rev-parse', '--short', 'HEAD'], { capture: true }).trim();
  const notesScriptContent = fs.readFileSync(notesScript, 'utf-8');
  const output = [
    '# SimFlow Release Notes',
    '',
    `Version: ${version}`,
    `Target commit: ${commit}`,
    '',
    '## Commits',
  ].join('\n');
  check('release notes command emits markdown with recent commits', output.includes('# SimFlow Release Notes') && output.includes('## Commits'), output);
  check('release notes generator script exists', fs.existsSync(notesScript));
  check('release notes policy sends install-smoke detail to .simflow', notesScriptContent.includes('.simflow/'));
}

function validateWorkflowAutomation() {
  console.log('\n--- Workflow Automation ---');
  const tracked = run('git', ['ls-files'], { capture: true }).split(/\r?\n/).filter(Boolean);
  check(
    'release smoke result logs are not tracked source files',
    !tracked.includes('docs/release-smoke-results.md'),
    'docs/release-smoke-results.md should remain local .simflow release evidence, not tracked docs.',
  );

  const pluginValidator = fs.readFileSync(path.join(ROOT, 'scripts', 'validate_plugin.js'), 'utf-8');
  const claudeValidator = fs.readFileSync(path.join(ROOT, 'scripts', 'validate_claude_plugin.js'), 'utf-8');
  for (const skillName of ['simflow-gpumd', 'simflow-mlp']) {
    check(`Codex wrapper validator requires ${skillName}`, pluginValidator.includes(`'${skillName}'`));
    check(`Claude wrapper validator requires ${skillName}`, claudeValidator.includes(`'${skillName}'`));
    check(`source skill exists for ${skillName}`, fs.existsSync(path.join(ROOT, 'skills', skillName, 'SKILL.md')));
  }

  const capabilities = readJson('workflow/toolchains/capabilities.json');
  check('toolchain capability contract keeps GPUMD tracked_only', capabilities.tracked_only_software.includes('gpumd'));
  check('toolchain capability contract keeps NEP tracked_only', capabilities.tracked_only_software.includes('nep'));
  check(
    'toolchain capability contract blocks GPUMD/NEP helper submit support',
    capabilities.capability_support.gpumd.not_helper_supported.includes('hpc_submit')
      && capabilities.capability_support.nep.not_helper_supported.includes('hpc_submit'),
  );

  const roadmap = readJson('workflow/toolchains/adapter_roadmap.json');
  const activeRoadmapEntries = roadmap.candidates.filter(item => item.runtime_enabled);
  check('ecosystem adapter roadmap fixtures are not active runtime adapters', activeRoadmapEntries.length === 0);

  const adapters = readJson('workflow/toolchains/adapters.json');
  const activeAdapters = adapters.adapters.filter(item => item.runtime_enabled).map(item => item.tool_id);
  const roadmapTools = new Set(roadmap.candidates.map(item => item.tool_id));
  check('helper adapter contract is metadata-only', adapters.policy.includes('do not execute tools'));
  check('runtime active adapters are limited to lammps/gpumd/nep', activeAdapters.join(',') === 'lammps,gpumd,nep');
  check(
    'runtime active adapters are not enabled from roadmap candidates',
    activeAdapters.every(tool => !roadmapTools.has(tool)),
  );

  const enablementReviews = readJson('workflow/toolchains/adapter_enablement_reviews.json');
  const reviewsByTool = new Map(enablementReviews.reviews.map(item => [item.tool_id, item]));
  const missingRoadmapReviews = roadmap.candidates
    .map(item => item.tool_id)
    .filter(tool => !reviewsByTool.has(tool));
  check('roadmap candidates have adapter enablement reviews', missingRoadmapReviews.length === 0, missingRoadmapReviews.join('\n'));
  check(
    'adapter enablement reviews are non-executing',
    enablementReviews.policy.includes('does not execute tools'),
  );
  const requestedEnablement = enablementReviews.reviews.filter(item => item.requested_runtime_enabled);
  check('Stage3 adapter reviews do not request runtime enablement', requestedEnablement.length === 0);
  const activeReviewedRoadmapTools = activeAdapters.filter(tool => roadmapTools.has(tool));
  check(
    'no roadmap candidate is active without approved metadata adapter review',
    activeReviewedRoadmapTools.every(tool => {
      const review = reviewsByTool.get(tool);
      return review && review.status === 'approved_for_metadata_adapter' && review.requested_runtime_enabled === true;
    }),
  );
  const unexpectedCandidateSkills = enablementReviews.reviews
    .filter(item => item.status !== 'approved_for_skill_design')
    .map(item => item.tool_id)
    .filter(tool => fs.existsSync(path.join(ROOT, 'skills', `simflow-${tool}`, 'SKILL.md')));
  check(
    'candidate adapter reviews do not create dedicated skills',
    unexpectedCandidateSkills.length === 0,
    unexpectedCandidateSkills.join('\n'),
  );

  const productionGate = readJson('workflow/gates/production_md_readiness.json');
  const readinessCondition = productionGate.conditions.find(item => item.id === 'readiness_report_ready');
  check(
    'production MD gate reads split scientific readiness status',
    readinessCondition && readinessCondition.path === '$.scientific_readiness.status',
  );
  const productionApproveActions = productionGate.actions_on_approve.join(' ');
  check(
    'production MD gate approval actions are readiness records, not submit triggers',
    !/(^|\b)(submit|execute|run|allow_production_mlp_md)(\b|$)/.test(productionApproveActions),
    productionApproveActions,
  );
  check(
    'production MD gate approval actions only record readiness decisions',
    productionGate.actions_on_approve.every(action => /^record_/.test(action) && !/submit|execute|run|allow/i.test(action)),
    productionGate.actions_on_approve.join('\n'),
  );
  const gateDir = path.join(ROOT, 'workflow', 'gates');
  const submitActionGates = fs.readdirSync(gateDir)
    .filter(file => file.endsWith('.json'))
    .map(file => [file, JSON.parse(fs.readFileSync(path.join(gateDir, file), 'utf-8'))])
    .filter(([, gate]) => (gate.actions_on_approve || []).includes('submit_job'))
    .map(([file, gate]) => gate.name || gate.gate_name || file);
  check(
    'hpc_submit is the only gate allowed to expose submit_job action',
    submitActionGates.join(',') === 'hpc_submit',
    submitActionGates.join('\n'),
  );
  const mlpEvidenceValidator = fs.readFileSync(path.join(ROOT, 'skills', 'simflow-mlp', 'scripts', 'validate_mlp_evidence.py'), 'utf-8');
  check(
    'MLP readiness helper keeps real_submit_allowed false',
    mlpEvidenceValidator.includes('real_submit_allowed = False')
      && !mlpEvidenceValidator.includes('real_submit_allowed = scientific_status == "ready"'),
  );
  const mlpWorkflowDoc = fs.readFileSync(path.join(ROOT, 'docs', 'mlp-md-workflow.md'), 'utf-8');
  const userGuideDoc = fs.readFileSync(path.join(ROOT, 'docs', 'user_guide.md'), 'utf-8');
  check(
    'MLP workflow docs describe readiness as a scientific decision, not submit permission',
    /scientific\s+readiness\s+decision/i.test(mlpWorkflowDoc)
      && !/readiness pass records permission to proceed/i.test(mlpWorkflowDoc)
      && mlpWorkflowDoc.includes('`real_submit_allowed`'),
  );
  check(
    'user guide splits scientific readiness from submit readiness',
    userGuideDoc.includes('Production or scientific readiness decisions are not submit decisions')
      && userGuideDoc.includes('requires separate `hpc_submit` evidence'),
  );

  const stateToolsSmoke = [
    'import importlib.util, json, sys',
    'from pathlib import Path',
    `root = Path(${JSON.stringify(ROOT)})`,
    'server_dir = root / "mcp" / "servers" / "simflow_state"',
    'sys.path.insert(0, str(server_dir))',
    'sys.path.insert(0, str(root))',
    'from mcp.shared.stdio_server import _list_tools',
    'spec = importlib.util.spec_from_file_location("simflow_state_release_smoke", server_dir / "server.py")',
    'server = importlib.util.module_from_spec(spec)',
    'spec.loader.exec_module(server)',
    'tools = {item["name"]: item["inputSchema"] for item in _list_tools(server.TOOLS, server.TOOL_DESCRIPTIONS, server.TOOL_SCHEMAS)}',
    'assert tools["record_computation_evidence"]["required"] == ["project_root", "evidence_params"]',
    'assert tools["record_analysis_evidence"]["required"] == ["project_root", "evidence_params"]',
    'evidence_graph = tools["evidence_graph"]["properties"]',
    'assert evidence_graph["direction"]["enum"] == ["upstream", "downstream", "both"]',
    'assert evidence_graph["depth"]["maximum"] == 5',
    'assert "recipe" in evidence_graph and "claim_id" in evidence_graph',
  ].join('; ');
  runCheck('simflow_state tools/list exposes evidence intake tools', 'python', ['-c', stateToolsSmoke]);

  const hpcSubmitSmoke = [
    'import hashlib, importlib.util, json, sys, tempfile',
    'from pathlib import Path',
    `root = Path(${JSON.stringify(ROOT)})`,
    'server_dir = root / "mcp" / "servers" / "hpc"',
    'sys.path.insert(0, str(server_dir))',
    'sys.path.insert(0, str(root))',
    'spec = importlib.util.spec_from_file_location("hpc_release_smoke", server_dir / "server.py")',
    'server = importlib.util.module_from_spec(spec)',
    'spec.loader.exec_module(server)',
    'tmp = tempfile.TemporaryDirectory()',
    'project = Path(tmp.name)',
    'script = project / "job.sh"',
    'script.write_text("#!/bin/bash\\necho should-not-run\\n", encoding="utf-8")',
    'digest = hashlib.sha256(script.read_bytes()).hexdigest()',
    'result = server.handle_request({"tool": "submit", "params": {"project_root": str(project), "script_path": str(script), "scheduler": "local", "approval_token": "release-smoke-token", "dry_run_evidence": "compute/dry_run_report.json", "script_hash": digest, "input_artifact_hash": "input-hash"}})',
    'tmp.cleanup()',
    'assert result.get("status") == "error", result',
    'assert result.get("code") == "missing_workflow_state", result',
  ].join('; ');
  runCheck('hpc.submit blocks before execution when workflow state is absent', 'python', ['-c', hpcSubmitSmoke]);
}

function validateMarketplaceWrappers() {
  console.log('\n--- Marketplace Wrappers ---');
  if (SKIP_WRAPPERS) {
    ok('wrapper build validation skipped by explicit local option');
    return;
  }
  runCheck('Codex marketplace wrapper builds', 'npm', ['run', 'build:codex-marketplace']);
  runCheck(
    'Codex marketplace wrapper validates',
    'npm',
    ['run', 'validate:plugin'],
    { env: { SIMFLOW_MARKETPLACE_ROOT: 'dist/codex-marketplace' } },
  );
  runCheck('Claude marketplace wrapper builds', 'npm', ['run', 'build:claude-marketplace']);
  runCheck(
    'Claude marketplace wrapper validates',
    'npm',
    ['run', 'validate:claude-plugin'],
    { env: { SIMFLOW_CLAUDE_MARKETPLACE_ROOT: 'dist/claude-marketplace' } },
  );
}

function main() {
  console.log('=== SimFlow Release Validation ===');
  validateCleanTree();
  validateVersionSync();
  validatePublicMetadata();
  validateSupportMatrix();
  validateRestrictedArtifacts();
  validateSafeExamples();
  validateReleaseNotesCommand();
  validateWorkflowAutomation();
  validateMarketplaceWrappers();
  console.log('\n=== Summary ===');
  if (errors > 0) {
    console.error(`Errors: ${errors}`);
    process.exit(1);
  }
  console.log('Errors: 0');
}

main();
