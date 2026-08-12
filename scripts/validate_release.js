#!/usr/bin/env node
/**
 * Validate source and marketplace release gates before publishing SimFlow.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const {
  compareSemver,
  diffSkillNames,
  resolveGitBranchRef,
} = require('./marketplace_version_guard');

const ROOT = path.resolve(__dirname, '..');
const args = new Set(process.argv.slice(2));
const ALLOW_DIRTY = args.has('--allow-dirty') || process.env.SIMFLOW_RELEASE_ALLOW_DIRTY === '1';
const SKIP_WRAPPERS = args.has('--skip-wrapper-build') || process.env.SIMFLOW_RELEASE_SKIP_WRAPPERS === '1';
const RESTRICTED_NAMES = new Set(['POTCAR', 'WAVECAR', 'CHGCAR', 'OUTCAR', 'vasprun.xml']);
const POTCAR_HEADER_RE = /PAW_PBE Si|VRHFIN =Si/;
const EXPECTED_PUBLIC_SKILLS = [
  'simflow',
  'simflow-analysis-visualization',
  'simflow-computation',
  'simflow-cp2k',
  'simflow-gpumd',
  'simflow-lammps',
  'simflow-literature-review',
  'simflow-mlp',
  'simflow-modeling',
  'simflow-proposal',
  'simflow-vasp',
  'simflow-writing',
];

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

function listFilesRecursive(relativeRoot, predicate = () => true) {
  const absoluteRoot = path.join(ROOT, relativeRoot);
  if (!fs.existsSync(absoluteRoot)) {
    return [];
  }
  const files = [];
  const stack = [absoluteRoot];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
      } else if (entry.isFile()) {
        const relativePath = path.relative(ROOT, fullPath);
        if (predicate(relativePath)) {
          files.push(relativePath);
        }
      }
    }
  }
  return files.sort();
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
  const codexConfig = fs.readFileSync(path.join(ROOT, '.codex', 'config.toml'), 'utf-8');
  const codexConfigMatch = codexConfig.match(/^version\s*=\s*"([^"]+)"/m);
  const codexConfigVersion = codexConfigMatch ? codexConfigMatch[1] : null;
  const versions = {
    'package.json': packageVersion,
    'pyproject.toml': pyprojectVersion,
    '.codex-plugin/plugin.json': codexVersion,
    '.claude-plugin/plugin.json': claudeVersion,
    '.codex/config.toml': codexConfigVersion,
  };
  const unique = new Set(Object.values(versions));
  check(
    'package, Python, Codex, Claude, and Codex config versions match',
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
    'opencode/simflow.mjs',
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
  const currentDocumentationFiles = [
    'README.md',
    'AGENTS.md',
    ...listFilesRecursive('docs', relativePath => relativePath.endsWith('.md')),
    ...listFilesRecursive('skills', relativePath => relativePath.endsWith('.md')),
  ].filter((relativePath, index, items) => (
    relativePath !== 'CHANGELOG.md' && items.indexOf(relativePath) === index
  ));
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
  check(
    'README states unsupported engines have no placeholder Skill',
    /Unsupported engines do not receive placeholder Skills\./.test(readme),
  );
  check(
    'PRD states supported Domain Skills explicitly',
    /Built-in Domain Skills cover VASP, CP2K, LAMMPS, GPUMD\/NEP, and general MLP\s+methodology\./.test(prd),
  );
  check('software skills document no-placeholder policy', /Unsupported engines do not receive placeholder Skills/.test(softwareSkills));

  const removedPublicSkills = [
    'simflow-safety-gates',
    'simflow-checkpoint',
    'simflow-handoff',
    'simflow-verify',
    'simflow-qe',
    'simflow-gaussian',
  ].filter(name => fs.existsSync(path.join(ROOT, 'skills', name, 'SKILL.md')));
  check(
    'operational and placeholder Skills are absent from the public surface',
    removedPublicSkills.length === 0,
    removedPublicSkills.join('\n'),
  );
  const operationalScriptDirs = ['simflow-safety-gates', 'simflow-checkpoint', 'simflow-handoff', 'simflow-verify'];
  const remainingOperationalScripts = operationalScriptDirs.flatMap(name => {
    const scriptsDir = path.join(ROOT, 'skills', name, 'scripts');
    if (!fs.existsSync(scriptsDir)) {
      return [];
    }
    return fs.readdirSync(scriptsDir, { recursive: true })
      .filter(relative => relative.endsWith('.py'))
      .map(relative => path.join('skills', name, 'scripts', relative));
  });
  check(
    'operational Skill script directories contain no Python entry points',
    remainingOperationalScripts.length === 0,
    remainingOperationalScripts.join('\n'),
  );

  const removedMcpServers = ['literature', 'structure', 'parsers', 'artifact_store', 'checkpoint_store'].filter(name => (
    fs.existsSync(path.join(ROOT, 'mcp', 'servers', name))
  ));
  check(
    'removed MCP server directories are absent',
    removedMcpServers.length === 0,
    removedMcpServers.join('\n'),
  );
  const analysisScript = fs.readFileSync(
    path.join(ROOT, 'skills', 'simflow-analysis-visualization', 'scripts', 'analyze_dft_results.py'),
    'utf-8',
  );
  check(
    'runtime analysis parser boundary excludes unsupported QE/Gaussian helpers',
    !/QEParser|GaussianParser|qe_parser|gaussian_parser/.test(analysisScript),
  );
  const unsupportedSourceFiles = [
    'runtime/simflow_helpers/engines/qe.py',
    'runtime/simflow_helpers/engines/parsers/qe_parser.py',
    'runtime/simflow_helpers/engines/parsers/gaussian_parser.py',
    'templates/qe/pw.in.template',
    'templates/qe/submit.slurm.template',
    'templates/gaussian/job.com.template',
    'templates/gaussian/submit.slurm.template',
  ].filter(relativePath => fs.existsSync(path.join(ROOT, relativePath)));
  check(
    'unsupported QE/Gaussian parser and template source files are absent',
    unsupportedSourceFiles.length === 0,
    unsupportedSourceFiles.join('\n'),
  );

  const targetStructure = fs.readFileSync(path.join(ROOT, 'docs', 'target-repo-structure.md'), 'utf-8');
  check(
    'target repo structure documents optional recipes and ships mlp_md',
    /recipes\/\s+# Optional reference paths/.test(targetStructure)
      && fs.existsSync(path.join(ROOT, 'workflow', 'recipes', 'mlp_md.json')),
  );

  const removedCustomSkillSurface = [
    'docs/custom-skills.md',
    'schemas/custom-skill-binding.schema.json',
    'schemas/custom-skill-metadata.schema.json',
    'schemas/skill-contract.schema.json',
  ].filter(relativePath => fs.existsSync(path.join(ROOT, relativePath)));
  check(
    'unused custom Skill extension surface remains removed',
    removedCustomSkillSurface.length === 0,
    removedCustomSkillSurface.join('\n'),
  );

  const customSkillClaims = [];
  for (const relativePath of currentDocumentationFiles) {
    const content = fs.readFileSync(path.join(ROOT, relativePath), 'utf-8');
    if (/custom skills?|\.simflow\/extensions\/skills|custom-skill-(?:binding|metadata)/i.test(content)) {
      customSkillClaims.push(relativePath);
    }
  }
  check(
    'public product docs do not advertise custom Skill discovery or overrides',
    customSkillClaims.length === 0,
    customSkillClaims.join('\n'),
  );

  const staleMemoryOrCredentialClaims = [];
  const staleClaimPatterns = [
    /six[- ](?:entry|entries|entry types?)/i,
    /\bMP_API_KEY\b/,
    /Materials Project/i,
    /Crystallography Open Database/i,
    /\bCOD\b.{0,40}(?:connector|credential|API)/i,
  ];
  for (const relativePath of currentDocumentationFiles) {
    const content = fs.readFileSync(path.join(ROOT, relativePath), 'utf-8');
    for (const pattern of staleClaimPatterns) {
      if (pattern.test(content)) {
        staleMemoryOrCredentialClaims.push(`${relativePath}: ${pattern}`);
      }
    }
  }
  check(
    'current docs describe four-entry memory and only implemented credential integrations',
    staleMemoryOrCredentialClaims.length === 0,
    staleMemoryOrCredentialClaims.join('\n'),
  );
}

function validateSimplificationContract() {
  console.log('\n--- Simplification Contract ---');
  check(
    'legacy workflow notification templates remain absent from the source tree',
    !fs.existsSync(path.join(ROOT, 'notifications')),
    'notifications/',
  );
  const publicSkills = fs.readdirSync(path.join(ROOT, 'skills'))
    .filter(name => fs.existsSync(path.join(ROOT, 'skills', name, 'SKILL.md')))
    .sort();
  check(
    'public Skill surface is exactly one Router, six Task, and five Domain Skills',
    JSON.stringify(publicSkills) === JSON.stringify(EXPECTED_PUBLIC_SKILLS),
    publicSkills.join('\n'),
  );

  const stateToolFiles = fs.readdirSync(path.join(ROOT, 'mcp', 'servers', 'simflow_state', 'tools'))
    .filter(name => name.endsWith('.py'))
    .sort();
  check(
    'simflow_state implementation directory contains only four public tools',
    JSON.stringify(stateToolFiles) === JSON.stringify(['checkpoint.py', 'inspect.py', 'record.py', 'recover.py']),
    stateToolFiles.join('\n'),
  );

  let auditReports = [];
  try {
    auditReports = JSON.parse(run('python', ['scripts/audit_skill_scripts.py', '--json'], { capture: true }));
  } catch (error) {
    fail('public Skill scripts can be audited', error.message);
  }
  const scriptViolations = auditReports.filter(report => (
    report.category === 'stage_runner'
      || report.stage_runner_functions.length > 0
      || report.stateful_runtime_calls.length > 0
  ));
  check(
    'public Skill scripts contain no stage runners or stateful runtime calls',
    auditReports.length > 0 && scriptViolations.length === 0,
    JSON.stringify(scriptViolations, null, 2),
  );

  const tracked = run('git', ['ls-files'], { capture: true }).split(/\r?\n/).filter(Boolean);
  const staleSkillPatterns = [
    /QE and Gaussian skills are reserved placeholders/i,
    /Stage runners may\s+ingest\/register outputs/i,
    /^\s*-\s*Register [^\n]+ as (?:separate )?artifacts\./im,
    /record user-provided [^\n]+ as generic artifacts/i,
    /canonical stage artifacts/i,
  ];
  const staleSkillFindings = [];
  for (const relativePath of tracked.filter(item => item.startsWith('skills/') && /\.(?:md|py)$/.test(item))) {
    const content = fs.readFileSync(path.join(ROOT, relativePath), 'utf-8');
    for (const pattern of staleSkillPatterns) {
      if (pattern.test(content)) {
        staleSkillFindings.push(`${relativePath}: ${pattern}`);
      }
    }
  }
  check(
    'public Skill text contains no runtime registration or placeholder instructions',
    staleSkillFindings.length === 0,
    staleSkillFindings.join('\n'),
  );

  const removedLifecycleTools = new Set([
    'begin_experiment.py',
    'begin_iteration.py',
    'compare_experiments.py',
    'evaluate_iteration.py',
    'experiment_timeline.py',
    'finish_activity.py',
    'finish_experiment.py',
    'fork_experiment.py',
    'migrate_experiment_ledger.py',
    'rebuild_experiment_exports.py',
    'resume_experiment.py',
    'session_handoff.py',
    'start_activity.py',
    'verify_experiment_ledger.py',
  ]);
  const removedStateSources = new Set([
    'runtime/simflow_core/engagement.py',
    'runtime/simflow_core/experiment_memory.py',
    'schemas/experiment_memory.schema.json',
  ]);
  const lifecycleFindings = tracked.filter(relativePath => (
    removedStateSources.has(relativePath)
      || (
        relativePath.startsWith('mcp/servers/simflow_state/tools/')
        && removedLifecycleTools.has(path.basename(relativePath))
      )
  ));
  check(
    'legacy SQLite/session/activity ledger ceremony remains absent from tracked runtime sources',
    lifecycleFindings.length === 0,
    lifecycleFindings.join('\n'),
  );

  const requiredMemorySources = [
    'runtime/simflow_core/experiment_notebook.py',
    'runtime/simflow_core/project_summary.py',
    'schemas/experiment_notebook.schema.json',
  ];
  check(
    'compact Experiment notebook module, summary rebuild, and schema are release-required',
    requiredMemorySources.every(relativePath => tracked.includes(relativePath))
      && /def rebuild_project_summary\(/.test(fs.readFileSync(path.join(ROOT, 'runtime', 'simflow_core', 'project_summary.py'), 'utf-8')),
    requiredMemorySources.filter(relativePath => !tracked.includes(relativePath)).join('\n'),
  );

  const sqliteLedgerFindings = tracked.filter(relativePath => (
    /^(?:runtime|mcp)\/.*\.py$/.test(relativePath)
      && /(?:^|\n)\s*(?:import sqlite3|from sqlite3 import)/.test(fs.readFileSync(path.join(ROOT, relativePath), 'utf-8'))
  ));
  check(
    'tracked runtime contains no SQLite ledger implementation',
    sqliteLedgerFindings.length === 0,
    sqliteLedgerFindings.join('\n'),
  );

  const notebookSource = fs.readFileSync(path.join(ROOT, 'runtime', 'simflow_core', 'experiment_notebook.py'), 'utf-8');
  const bindingSource = fs.readFileSync(path.join(ROOT, 'runtime', 'simflow_core', 'run_bindings.py'), 'utf-8');
  const jobRecordSource = fs.readFileSync(path.join(ROOT, 'runtime', 'simflow_helpers', 'computation', 'job_records.py'), 'utf-8');
  const notebookSchema = readJson('schemas/experiment_notebook.schema.json');
  const ontology = notebookSchema.properties.entry_type.enum;
  check(
    'Experiment Memory v1 ontology is capped at four entry types with no action field',
    JSON.stringify(ontology) === JSON.stringify(['experiment', 'attempt', 'observation', 'decision'])
      && !Object.prototype.hasOwnProperty.call(notebookSchema.properties, 'action')
      && !notebookSchema.required.includes('action')
      && !/material_action|MATERIAL_ACTION|RECOVERABILITY/.test(notebookSource),
    JSON.stringify({ ontology, properties: Object.keys(notebookSchema.properties) }),
  );
  check(
    'HPC consumes existing Attempt references and Run identity remains independent',
    /get_attempt_entry\(/.test(bindingSource)
      && !/def _attempt_id\(|uuid\.uuid4\(\).*att_/.test(bindingSource)
      && !/run_id\s*=\s*attempt_id|attempt_id\s+or\s+f["']/.test(`${bindingSource}\n${jobRecordSource}`),
    'run_bindings.py or job_records.py can synthesize an Attempt or reuse it as run_id',
  );

  const memoryContractSmoke = [
    'import importlib.util, json, sys, tempfile',
    'from pathlib import Path',
    'from runtime.simflow_core.experiment_notebook import append_experiment_entry, create_experiment',
    'from runtime.simflow_core.project_summary import rebuild_project_summary',
    'from runtime.simflow_core.records import record_event',
    'tmp = tempfile.TemporaryDirectory()',
    'root = Path(tmp.name)',
    'experiment = create_experiment(str(root), title="Temperature scope", research_question="Exclude >= 400 K?", scope_paths=["."])',
    'attempt = append_experiment_entry(str(root), experiment_id=experiment["experiment_id"], entry_type="attempt", attempt_id="att_release", summary="Evaluate the exclusion strategy")',
    'append_experiment_entry(str(root), experiment_id=experiment["experiment_id"], entry_type="decision", attempt_id=attempt["entry"]["attempt_id"], summary="Exclude high-temperature frames")',
    '(root / "before.xyz").write_text("before\\n", encoding="utf-8")',
    '(root / "after.xyz").write_text("after\\n", encoding="utf-8")',
    'change = record_event(str(root), kind="evidence_change", summary="Filtered dataset", operation="filter", targets=["before.xyz"], before_refs=["before.xyz"], after_refs=["after.xyz"], outcome="completed", experiment_id=experiment["experiment_id"], attempt_id=attempt["entry"]["attempt_id"])',
    'assert change["kind"] == "evidence_change" and "status" not in change',
    'checkpoint_dir = root / ".simflow" / "checkpoints"',
    'checkpoint_dir.mkdir(parents=True)',
    '(checkpoint_dir / "ckpt_release.json").write_text(json.dumps({"checkpoint_id": "ckpt_release"}), encoding="utf-8")',
    'summary = rebuild_project_summary(str(root))',
    'assert summary["counts"]["experiments"] == 1',
    'assert summary["counts"]["operational_total"] == 1',
    'assert summary["counts"]["checkpoints"] == 1',
    '(root / ".simflow" / "project.json").unlink()',
    'rebuilt = rebuild_project_summary(str(root), write=False)',
    'assert rebuilt["experiments"][0]["research_question"] == "Exclude >= 400 K?"',
    'mcp_dir = Path("mcp/servers/simflow_state").resolve()',
    'sys.path.insert(0, str(mcp_dir))',
    'spec = importlib.util.spec_from_file_location("release_state_server", mcp_dir / "server.py")',
    'server = importlib.util.module_from_spec(spec)',
    'spec.loader.exec_module(server)',
    'assert set(server.TOOLS) == {"inspect", "record", "checkpoint", "recover"}',
    'branches = server.TOOL_SCHEMAS["record"]["oneOf"]',
    'assert len(branches) == 6',
    'assert branches[1]["properties"]["kind"]["const"] == "evidence_change"',
    'assert all(branches[1]["properties"][field] is False for field in ("status", "stage", "run_id", "goal", "next_action", "artifacts", "details", "checkpoint_id"))',
    'assert {item["properties"]["entry_type"]["const"] for item in branches[2:]} == {"experiment", "attempt", "observation", "decision"}',
    'assert "action" not in server.TOOL_SCHEMAS["record"]["properties"]',
    'removed = server.handle_request({"tool": "record", "params": {"project_root": str(root), "channel": "experiment", "entry_type": "material_action", "summary": "removed", "payload": {}}})',
    'assert removed["status"] == "error"',
    'uninitialized = Path(tmp.name) / "uninitialized"',
    'inspected = server.handle_request({"tool": "inspect", "params": {"project_root": str(uninitialized)}})',
    'assert inspected["status"] == "success" and not (uninitialized / ".simflow").exists()',
    'tmp.cleanup()',
  ].join('\n');
  runCheck(
    'four-entry Experiment memory, immutable evidence changes, and read-only inspect are operational',
    'python',
    ['-c', memoryContractSmoke],
  );

  const runPlanBindingSmoke = [
    'import tempfile',
    'from pathlib import Path',
    'from mcp.servers.hpc.run_plan import build_run_plan',
    'tmp = tempfile.TemporaryDirectory()',
    'root = Path(tmp.name)',
    'script = root / "job.sh"',
    'script.write_text("#!/bin/sh\\ntrue\\n", encoding="utf-8")',
    '(root / "input.dat").write_text("input\\n", encoding="utf-8")',
    'base = {"scheduler": "local", "script_path": "job.sh", "input_paths": ["input.dat"]}',
    'first = build_run_plan(str(root), {**base, "experiment_id": "exp_aaaaaaaaaaaa", "attempt_id": "att_a"}, script=script, script_generated=False, validation={"status": "pass"})',
    'second = build_run_plan(str(root), {**base, "experiment_id": "exp_bbbbbbbbbbbb", "attempt_id": "att_b"}, script=script, script_generated=False, validation={"status": "pass"})',
    'assert first["run_plan_hash"] == second["run_plan_hash"]',
    'assert "experiment_id" not in first and "attempt_id" not in first',
    'tmp.cleanup()',
  ].join('\n');
  runCheck(
    'Experiment and Attempt bindings do not affect immutable run_plan_hash',
    'python',
    ['-c', runPlanBindingSmoke],
  );

  const migrationSmoke = [
    'import json, tempfile',
    'from pathlib import Path',
    'from runtime.simflow_core.migration import MigrationError, apply_migration, build_migration_report',
    'from runtime.simflow_core.records import list_project_records',
    'tmp = tempfile.TemporaryDirectory()',
    'root = Path(tmp.name)',
    'legacy = root / ".simflow" / "state" / "workflow.json"',
    'legacy.parent.mkdir(parents=True)',
    'legacy.write_text(json.dumps({"workflow_id": "PRIVATE_LEGACY_VALUE"}) + "\\n", encoding="utf-8")',
    'memory = root / ".simflow" / "memory" / "events.jsonl"',
    'memory.parent.mkdir(parents=True)',
    'memory.write_text(json.dumps({"event": "PRIVATE_MEMORY_VALUE"}) + "\\n", encoding="utf-8")',
    'source = {legacy: legacy.read_bytes(), memory: memory.read_bytes()}',
    'report = build_migration_report(str(root))',
    'assert report["detected"] is True',
    'assert report["safety"]["source_files_are_read_only"] is True',
    'assert report["safety"]["legacy_memory_content_is_not_imported"] is True',
    'assert "PRIVATE_LEGACY_VALUE" not in json.dumps(report)',
    'assert "PRIVATE_MEMORY_VALUE" not in json.dumps(report)',
    'assert all(path.read_bytes() == content for path, content in source.items())',
    'assert not (root / ".simflow" / "project.json").exists()',
    'assert not (root / ".simflow" / "records.jsonl").exists()',
    'assert not (root / ".simflow" / "reports").exists()',
    'blocked = False',
    'try:\n    apply_migration(str(root), migration_report_hash=report["migration_report_hash"], confirm_migration=False)\nexcept MigrationError:\n    blocked = True',
    'assert blocked is True',
    'applied = apply_migration(str(root), migration_report_hash=report["migration_report_hash"], confirm_migration=True)',
    'assert applied["status"] == "applied"',
    'assert len(list_project_records(str(root), kind="migration")) == 1',
    'assert all(path.read_bytes() == content for path, content in source.items())',
    'tmp.cleanup()',
  ].join('\n');
  runCheck(
    'legacy state and memory migration is metadata-only until explicit current-hash confirmation',
    'python',
    ['-c', migrationSmoke],
  );
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

  const restrictedRuntimeSmoke = [
    'import json, os, stat, tempfile',
    'from pathlib import Path',
    'tmp = tempfile.TemporaryDirectory()',
    'root = Path(tmp.name)',
    'os.environ.setdefault("MPLCONFIGDIR", str(root / "matplotlib"))',
    'from runtime.simflow_core.records import record_event',
    'from runtime.simflow_helpers.engines.vasp_potcar import generate_potcar',
    'secret = "release-secret-value-1234567890"',
    'record_event(str(root), kind="note", summary="sanitize", details={"password": secret, "api_key": secret, "private_key": secret, "potcar_body": secret, "message": "Bearer " + secret})',
    'records = (root / ".simflow" / "records.jsonl").read_text(encoding="utf-8")',
    'assert secret not in records',
    'assert "[REDACTED]" in records',
    'library = root / "licensed" / "PBE" / "Si"',
    'library.mkdir(parents=True)',
    'marker = "PRIVATE_POTCAR_MARKER"',
    '(library / "POTCAR").write_text("PAW_PBE Si 05Jan2001\\nPOMASS = 1.0; ZVAL = 4.0\\nEnd of Dataset " + marker + "\\n", encoding="utf-8")',
    'calc = root / "calculation" / "si"',
    'calc.mkdir(parents=True)',
    'poscar = calc / "POSCAR"',
    'poscar.write_text("Test\\n1.0\\n5 0 0\\n0 5 0\\n0 0 5\\nSi\\n1\\nDirect\\n0 0 0\\n", encoding="utf-8")',
    'result = generate_potcar(str(poscar), str(calc / "POTCAR"), potcar_root=str(root / "licensed"), setups="minimal", project_root=str(root))',
    'assert result["status"] == "materialized", result',
    'assert result["content_included"] is False',
    'assert result["resolved_datasets"] == ["Si"]',
    'assert marker not in json.dumps(result)',
    'assert str(root / "licensed") not in json.dumps(result)',
    'assert stat.S_IMODE((calc / "POTCAR").stat().st_mode) == 0o600',
    'blocked = generate_potcar(str(poscar), str(root / ".simflow" / "POTCAR"), potcar_root=str(root / "licensed"), setups="minimal", project_root=str(root))',
    'assert blocked["reason_code"] == "restricted_potcar_output_location"',
    'tmp.cleanup()',
  ].join('\n');
  runCheck(
    'compact records redact credentials and POTCAR materialization remains metadata-only',
    'python',
    ['-c', restrictedRuntimeSmoke],
  );
}

function validateSafeExamples() {
  console.log('\n--- Safe Examples ---');
  const directExecutionPatterns = [
    /subprocess\.(?:run|Popen)\s*\(\s*\[\s*["'](?:ssh|scp)["']/,
    /(?:^|[;&|]\s*)ssh\s+[^\n]+/m,
    /(?:^|[;&|]\s*)scp\s+[^\n]+/m,
    /\bsbatch\b/,
    /--submit\b/,
  ];
  const directExecutionFindings = [];
  for (const relativePath of listFilesRecursive('examples', item => /\.(?:py|sh)$/.test(item))) {
    const content = fs.readFileSync(path.join(ROOT, relativePath), 'utf-8');
    for (const pattern of directExecutionPatterns) {
      if (pattern.test(content)) {
        directExecutionFindings.push(`${relativePath}: ${pattern}`);
      }
    }
  }
  check(
    'examples contain no direct SSH, SCP, sbatch, or submit bypass path',
    directExecutionFindings.length === 0,
    directExecutionFindings.join('\n'),
  );

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
      check('safe dry-run example writes compact project state', fs.existsSync(path.join(exampleRoot, '.simflow', 'project.json')));
      check('safe dry-run example records plan and deliverable', summary.record_count === 2 && fs.existsSync(path.join(exampleRoot, '.simflow', 'records.jsonl')), result.stdout);
      check('safe dry-run example persists immutable run plan', fs.existsSync(path.join(exampleRoot, summary.important_paths.run_plan)), result.stdout);
      check('safe dry-run example blocks submit without approval', summary.submit_blocked === true && summary.approval_required === true, result.stdout);
      check('safe dry-run example creates no legacy registries or checkpoints', !fs.existsSync(path.join(exampleRoot, '.simflow', 'state')) && summary.checkpoint_count === 0, result.stdout);
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
      check('LAMMPS safe dry-run example records plan and deliverable', summary.record_count === 2 && fs.existsSync(path.join(lammpsRoot, '.simflow', 'records.jsonl')), result.stdout);
      check('LAMMPS safe dry-run example embeds credential scan in run plan', summary.credential_scan_status === 'pass' || summary.credential_scan_status === 'warning', result.stdout);
      check('LAMMPS safe dry-run example blocks submit without approval', summary.submit_blocked === true && summary.approval_required === true, result.stdout);
      check('LAMMPS safe dry-run example creates no legacy registries or checkpoints', !fs.existsSync(path.join(lammpsRoot, '.simflow', 'state')) && summary.checkpoint_count === 0, result.stdout);
    }
  } finally {
    fs.rmSync(lammpsRoot, { recursive: true, force: true });
  }

  const cp2kRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'simflow-cp2k-safe-example-'));
  try {
    const result = spawnSync(
      'python',
      ['examples/h2o/run_cp2k_workflow.py', '--dry-run', '--output-dir', cp2kRoot],
      {
        cwd: ROOT,
        env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
        encoding: 'utf-8',
        stdio: 'pipe',
      },
    );
    if (result.status !== 0) {
      fail('H2O CP2K input-only example completes', [result.stdout, result.stderr].filter(Boolean).join('\n'));
    } else {
      let summary = {};
      try {
        summary = JSON.parse(result.stdout);
      } catch (error) {
        fail('H2O CP2K input-only example emits JSON summary', result.stdout);
      }
      check(
        'H2O CP2K input-only example completes without runtime state',
        summary.status === 'prepared'
          && summary.real_execution === false
          && fs.existsSync(path.join(cp2kRoot, 'aimd', 'aimd_nvt.inp'))
          && fs.existsSync(path.join(cp2kRoot, 'dry_run_summary.json'))
          && !fs.existsSync(path.join(cp2kRoot, '.simflow')),
        result.stdout,
      );
    }
  } finally {
    fs.rmSync(cp2kRoot, { recursive: true, force: true });
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
  check('release notes require OpenCode install smoke', notesScriptContent.includes('Codex, Claude, and OpenCode'));
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
  const opencodeValidator = fs.readFileSync(path.join(ROOT, 'scripts', 'validate_opencode_plugin.js'), 'utf-8');
  for (const skillName of ['simflow-gpumd', 'simflow-mlp']) {
    check(`Codex wrapper validator requires ${skillName}`, pluginValidator.includes(`'${skillName}'`));
    check(`Claude wrapper validator requires ${skillName}`, claudeValidator.includes(`'${skillName}'`));
    check(`OpenCode package validator requires ${skillName}`, opencodeValidator.includes(`'${skillName}'`));
    check(`source skill exists for ${skillName}`, fs.existsSync(path.join(ROOT, 'skills', skillName, 'SKILL.md')));
  }

  const hostAdaptation = fs.readFileSync(path.join(ROOT, 'runtime', 'simflow_core', 'host_adaptation.py'), 'utf-8');
  check('host adaptation recognizes OpenCode clientInfo', hostAdaptation.includes('"opencode"'));
  check('OpenCode source adapter exists', fs.existsSync(path.join(ROOT, '.opencode', 'plugins', 'simflow.js')));
  check('OpenCode canonical plugin module exists', fs.existsSync(path.join(ROOT, 'opencode', 'simflow.mjs')));

  const capabilities = readJson('workflow/toolchains/capabilities.json');
  check('toolchain capability contract marks GPUMD helper-supported', capabilities.helper_supported_software.includes('gpumd'));
  check('toolchain capability contract marks NEP helper-supported', capabilities.helper_supported_software.includes('nep'));
  check(
    'toolchain capability contract blocks GPUMD/NEP real execution and submit support',
    capabilities.capability_support.gpumd.not_helper_supported.includes('hpc_submit')
      && capabilities.capability_support.nep.not_helper_supported.includes('hpc_submit')
      && capabilities.capability_support.gpumd.not_helper_supported.includes('real_execution')
      && capabilities.capability_support.nep.not_helper_supported.includes('real_execution'),
  );

  const roadmap = readJson('workflow/toolchains/adapter_roadmap.json');
  const activeRoadmapEntries = roadmap.candidates.filter(item => item.runtime_enabled);
  check('ecosystem adapter roadmap fixtures are not active runtime adapters', activeRoadmapEntries.length === 0);

  const adapters = readJson('workflow/toolchains/adapters.json');
  const activeAdapters = adapters.adapters.filter(item => item.runtime_enabled).map(item => item.tool_id);
  const roadmapTools = new Set(roadmap.candidates.map(item => item.tool_id));
  check('helper adapter contract blocks execution', adapters.policy.includes('never execute tools'));
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
  const executionActionGates = fs.readdirSync(gateDir)
    .filter(file => file.endsWith('.json'))
    .map(file => [file, JSON.parse(fs.readFileSync(path.join(gateDir, file), 'utf-8'))])
    .filter(([, gate]) => (gate.actions_on_approve || []).some(action => /submit|execute|transfer_files|record_job_id/i.test(action)))
    .map(([file, gate]) => gate.name || gate.gate_name || file);
  check(
    'workflow review gates expose no execution actions',
    executionActionGates.length === 0,
    executionActionGates.join('\n'),
  );

  const gateRuntime = fs.readFileSync(path.join(ROOT, 'runtime', 'simflow_core', 'gates.py'), 'utf-8');
  check(
    'compatibility HPC gates cannot authorize execution',
    gateRuntime.includes('RUNTIME_OWNED_GATES = {"hpc_submit", "hpc_transfer"}')
      && gateRuntime.includes('public_hpc_runtime_required'),
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
    'assert set(tools) == {"inspect", "record", "checkpoint", "recover"}',
    'assert tools["inspect"]["required"] == ["project_root"]',
    'assert tools["record"]["oneOf"][0]["required"] == ["project_root", "kind", "summary"]',
    'assert len(tools["record"]["oneOf"]) == 6',
    'assert tools["checkpoint"]["required"] == ["project_root", "summary"]',
    'assert tools["recover"]["required"] == ["project_root"]',
  ].join('; ');
  runCheck('simflow_state tools/list exposes four compact tools', 'python', ['-c', stateToolsSmoke]);

  const hpcSubmitSmoke = [
    'import importlib.util, json, sys, tempfile',
    'from pathlib import Path',
    `root = Path(${JSON.stringify(ROOT)})`,
    'server_dir = root / "mcp" / "servers" / "hpc"',
    'sys.path.insert(0, str(server_dir))',
    'sys.path.insert(0, str(root))',
    'spec = importlib.util.spec_from_file_location("hpc_release_smoke", server_dir / "server.py")',
    'server = importlib.util.module_from_spec(spec)',
    'spec.loader.exec_module(server)',
    'from mcp.shared.stdio_server import _list_tools',
    'tools = {item["name"]: item["inputSchema"] for item in _list_tools(server.TOOLS, server.TOOL_DESCRIPTIONS, server.TOOL_SCHEMAS)}',
    'assert set(tools) == {"plan", "transfer", "submit", "status"}',
    'assert tools["plan"]["required"] == ["project_root", "script_path", "input_paths"]',
    'assert tools["submit"]["required"] == ["project_root", "run_plan_hash"]',
    'assert not ({"dry_run_evidence", "script_hash", "input_artifact_hash"} & set(tools["submit"]["properties"]))',
    'tmp = tempfile.TemporaryDirectory()',
    'project = Path(tmp.name)',
    'script = project / "job.sh"',
    'input_file = project / "input.dat"',
    'script.write_text("#!/bin/bash\\necho should-not-run\\n", encoding="utf-8")',
    'script.chmod(0o755)',
    'input_file.write_text("input\\n", encoding="utf-8")',
    'planned = server.handle_request({"tool": "plan", "params": {"project_root": str(project), "script_path": "job.sh", "input_paths": ["input.dat"], "scheduler": "local"}})',
    'assert planned.get("status") == "success", planned',
    'run_plan_hash = planned["data"]["run_plan_hash"]',
    'result = server.handle_request({"tool": "submit", "params": {"project_root": str(project), "run_plan_hash": run_plan_hash}})',
    'assert result.get("status") == "error", result',
    'assert result.get("approval_required") is True, result',
    'assert result.get("run_plan_hash") == run_plan_hash, result',
    'secret = "do-not-store-release-secret"',
    'input_file.write_text("api_key=" + secret + "\\n", encoding="utf-8")',
    'credential_plan = server.handle_request({"tool": "plan", "params": {"project_root": str(project), "script_path": "job.sh", "input_paths": ["input.dat"], "scheduler": "local"}})',
    'assert credential_plan.get("status") == "error", credential_plan',
    'assert credential_plan["data"]["credential_scan"]["status"] == "fail", credential_plan',
    'assert secret not in json.dumps(credential_plan)',
    'persisted = "\\n".join(path.read_text(encoding="utf-8") for path in (project / ".simflow").rglob("*.json"))',
    'assert secret not in persisted',
    'tmp.cleanup()',
  ].join('; ');
  runCheck('hpc exposes four immutable-plan tools, bound approval, and fail-closed credential scans', 'python', ['-c', hpcSubmitSmoke]);
}

function gitShow(ref, relativePath) {
  return run('git', ['show', `${ref}:${relativePath}`], { capture: true });
}

function gitListTree(ref, relativePath) {
  return run('git', ['ls-tree', '-r', '--name-only', ref, '--', relativePath], { capture: true })
    .split(/\r?\n/)
    .filter(Boolean);
}

function validateMarketplaceVersionGuard() {
  console.log('\n--- Marketplace Version Guard ---');
  const currentVersion = readJson('package.json').version;
  const currentSkills = fs.readdirSync(path.join(ROOT, 'skills'))
    .filter(entry => fs.existsSync(path.join(ROOT, 'skills', entry, 'SKILL.md')))
    .sort();

  for (const [label, branch, manifestPath] of [
    ['Codex', 'codex-marketplace', 'plugins/simflow/.codex-plugin/plugin.json'],
    ['Claude', 'claude-marketplace', 'plugins/simflow/.claude-plugin/plugin.json'],
  ]) {
    try {
      const branchRef = resolveGitBranchRef(branch, ROOT);
      const previousVersion = JSON.parse(gitShow(branchRef, manifestPath)).version;
      const previousSkills = gitListTree(branchRef, 'plugins/simflow/skills')
        .filter(file => file.endsWith('/SKILL.md'))
        .map(file => file.split('/').at(-2))
        .sort();
      const diff = diffSkillNames(currentSkills, previousSkills);
      const skillsChanged = diff.added.length > 0 || diff.removed.length > 0;
      const versionIncreased = compareSemver(currentVersion, previousVersion) > 0;
      check(
        `${label} marketplace packaged skill changes require plugin version bump`,
        !skillsChanged || versionIncreased,
        [
          `current version: ${currentVersion}`,
          `previous ${branchRef} version: ${previousVersion}`,
          diff.added.length ? `added skills: ${diff.added.join(', ')}` : null,
          diff.removed.length ? `removed skills: ${diff.removed.join(', ')}` : null,
        ].filter(Boolean).join('\n'),
      );
    } catch (error) {
      fail(`${label} marketplace packaged skill/version guard can inspect ${branch} or origin/${branch}`, error.message);
    }
  }
}

function validateMarketplaceWrappers() {
  console.log('\n--- Host Distributions ---');
  if (SKIP_WRAPPERS) {
    ok('wrapper build validation skipped by explicit local option');
    return;
  }
  const sourceVersion = readJson('package.json').version;
  const checkBuiltVersion = (label, relativePath) => {
    try {
      const builtVersion = readJson(relativePath).version;
      check(label, builtVersion === sourceVersion, `source=${sourceVersion} built=${builtVersion}`);
    } catch (error) {
      fail(label, error.message);
    }
  };
  runCheck('Codex marketplace wrapper builds', 'npm', ['run', 'build:codex-marketplace']);
  checkBuiltVersion(
    'built Codex marketplace version matches source',
    'dist/codex-marketplace/plugins/simflow/.codex-plugin/plugin.json',
  );
  runCheck(
    'Codex marketplace wrapper validates',
    'npm',
    ['run', 'validate:plugin'],
    { env: { SIMFLOW_MARKETPLACE_ROOT: 'dist/codex-marketplace' } },
  );
  runCheck('Claude marketplace wrapper builds', 'npm', ['run', 'build:claude-marketplace']);
  checkBuiltVersion(
    'built Claude marketplace version matches source',
    'dist/claude-marketplace/plugins/simflow/.claude-plugin/plugin.json',
  );
  runCheck(
    'Claude marketplace wrapper validates',
    'npm',
    ['run', 'validate:claude-plugin'],
    { env: { SIMFLOW_CLAUDE_MARKETPLACE_ROOT: 'dist/claude-marketplace' } },
  );
  runCheck('OpenCode npm package builds', 'npm', ['run', 'build:opencode-plugin']);
  checkBuiltVersion(
    'built OpenCode package version matches source',
    'dist/opencode-plugin/package.json',
  );
  runCheck(
    'OpenCode npm package validates',
    'npm',
    ['run', 'validate:opencode-plugin'],
    { env: { SIMFLOW_OPENCODE_PLUGIN_ROOT: 'dist/opencode-plugin' } },
  );
}

function main() {
  console.log('=== SimFlow Release Validation ===');
  validateCleanTree();
  validateVersionSync();
  validatePublicMetadata();
  validateSupportMatrix();
  validateSimplificationContract();
  validateRestrictedArtifacts();
  validateSafeExamples();
  validateReleaseNotesCommand();
  validateWorkflowAutomation();
  validateMarketplaceVersionGuard();
  validateMarketplaceWrappers();
  console.log('\n=== Summary ===');
  if (errors > 0) {
    console.error(`Errors: ${errors}`);
    process.exit(1);
  }
  console.log('Errors: 0');
}

main();
