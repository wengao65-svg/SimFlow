#!/usr/bin/env node
/** Validate the public Skill-only distribution before release. */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const ROOT = path.resolve(__dirname, '..');
const SKILLS = new Set(['simflow-literature-review', 'simflow-reference-extraction', 'simflow-proposal', 'simflow-modeling', 'simflow-computation', 'simflow-analysis-visualization', 'simflow-writing', 'simflow-vasp', 'simflow-cp2k', 'simflow-lammps', 'simflow-gpumd', 'simflow-mlp']);
const RETIRED = ['mcp', 'runtime', 'workflow', 'schemas', '.mcp.json', '.claude.mcp.json', '.simflow'];
let errors = 0;
function check(label, value) { console.log(`  ${value ? 'OK' : 'ERROR'}: ${label}`); if (!value) errors++; }
function json(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
function command(args, env = {}) { const result = spawnSync(args[0], args.slice(1), { cwd: ROOT, encoding: 'utf8', env: { ...process.env, ...env }, timeout: 30000 }); check(args.join(' '), result.status === 0); if (result.status !== 0) console.error(result.stderr || result.stdout); }
function validatePackage(root, manifest) {
  check(`${root} manifest exists`, fs.existsSync(path.join(root, manifest)));
  const dir = path.join(root, 'skills');
  if (!fs.existsSync(dir)) { check(`${root} Skills exist`, false); return; }
  const actual = fs.readdirSync(dir).filter(item => fs.existsSync(path.join(dir, item, 'SKILL.md')));
  check(`${root} has exactly 12 Skills`, actual.length === SKILLS.size && actual.every(item => SKILLS.has(item)));
  for (const item of RETIRED) check(`${root} excludes ${item}`, !fs.existsSync(path.join(root, item)));
  for (const skill of SKILLS) {
    for (const section of ['scripts', 'lib', 'assets']) {
      const source = path.join(ROOT, 'skills', skill, section);
      if (!fs.existsSync(source)) continue;
      const installed = path.join(dir, skill, section);
      check(`${root} includes ${skill}/${section}`, fs.existsSync(installed));
      if (fs.existsSync(installed)) {
        for (const entry of fs.readdirSync(source).filter(name => !name.startsWith('__pycache__') && !name.endsWith('.pyc'))) {
          check(`${root} includes ${skill}/${section}/${entry}`, fs.existsSync(path.join(installed, entry)));
        }
      }
    }
  }
  const forbidden = new Set(['POTCAR', 'WAVECAR', 'CHGCAR', 'OUTCAR', 'vasprun.xml']);
  const pending = [root]; let restricted = false;
  while (pending.length) {
    const current = pending.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (forbidden.has(entry.name)) restricted = true;
      if (entry.isDirectory()) pending.push(path.join(current, entry.name));
    }
  }
  check(`${root} excludes restricted artifacts`, !restricted);
}
console.log('=== SimFlow Skill Pack Release Validation ===');
const version = json(path.join(ROOT, 'package.json')).version;
for (const manifest of ['.codex-plugin/plugin.json', '.claude-plugin/plugin.json']) check(`${manifest} version matches`, json(path.join(ROOT, manifest)).version === version);
check('Codex config contains no execution permissions or approval settings', !/allow_shell|allow_hpc_submit|require_approval_for_submit/.test(fs.readFileSync(path.join(ROOT, '.codex', 'config.toml'), 'utf8')));
check('default MCP files absent', !fs.existsSync(path.join(ROOT, '.mcp.json')) && !fs.existsSync(path.join(ROOT, '.claude.mcp.json')));
const git = spawnSync('git', ['status', '--porcelain'], { cwd: ROOT, encoding: 'utf8' });
check('working tree clean or explicitly allowed for local validation', !git.stdout.trim() || process.env.SIMFLOW_RELEASE_ALLOW_DIRTY === '1');
command(['npm', 'run', 'validate:all']);
if (process.env.SIMFLOW_RELEASE_SKIP_WRAPPERS === '1') {
  console.log('  OK: wrapper build validation skipped');
} else {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'simflow-release-'));
  try {
    const codex = path.join(tmp, 'codex');
    const claude = path.join(tmp, 'claude');
    const opencode = path.join(tmp, 'opencode');
    command(['node', 'scripts/build_marketplace_wrapper.js', codex]);
    command(['node', 'scripts/build_claude_marketplace_wrapper.js', claude]);
    command(['node', 'scripts/build_opencode_plugin.js', opencode]);
    validatePackage(path.join(codex, 'plugins', 'simflow'), '.codex-plugin/plugin.json');
    validatePackage(path.join(claude, 'plugins', 'simflow'), '.claude-plugin/plugin.json');
    validatePackage(opencode, 'package.json');
    command(['node', 'scripts/validate_plugin.js'], { SIMFLOW_MARKETPLACE_ROOT: codex });
    command(['node', 'scripts/validate_claude_plugin.js'], { SIMFLOW_CLAUDE_MARKETPLACE_ROOT: claude });
    command(['node', 'scripts/validate_opencode_plugin.js'], { SIMFLOW_OPENCODE_PLUGIN_ROOT: opencode });
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
}
console.log(`Errors: ${errors}`);
process.exit(errors ? 1 : 0);
