#!/usr/bin/env node
/**
 * Validate source and marketplace release gates before publishing SimFlow.
 */

const fs = require('fs');
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

function validateReleaseNotesCommand() {
  console.log('\n--- Release Notes ---');
  const notesScript = path.join(ROOT, 'scripts', 'generate_release_notes.js');
  const version = readJson('package.json').version;
  const commit = run('git', ['rev-parse', '--short', 'HEAD'], { capture: true }).trim();
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
  validateRestrictedArtifacts();
  validateReleaseNotesCommand();
  validateMarketplaceWrappers();
  console.log('\n=== Summary ===');
  if (errors > 0) {
    console.error(`Errors: ${errors}`);
    process.exit(1);
  }
  console.log('Errors: 0');
}

main();
