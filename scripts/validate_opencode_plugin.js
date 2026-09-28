#!/usr/bin/env node
/** Validate that the OpenCode adapter adds Skills without altering MCP config. */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');
const { spawnSync } = require('child_process');
const ROOT = path.resolve(__dirname, '..');
const BUILT = process.env.SIMFLOW_OPENCODE_PLUGIN_ROOT;
const SKILLS = ['simflow-literature-review', 'simflow-reference-extraction', 'simflow-proposal', 'simflow-modeling', 'simflow-computation', 'simflow-analysis-visualization', 'simflow-writing', 'simflow-vasp', 'simflow-cp2k', 'simflow-lammps', 'simflow-gpumd', 'simflow-mlp'];
let errors = 0;
function check(label, condition, detail = '') { console.log(`  ${condition ? 'OK' : 'ERROR'}: ${label}`); if (!condition) { errors++; if (detail) console.error(detail); } }
function json(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
async function validateAdapter(root, entry) {
  const plugin = (await import(`${pathToFileURL(entry).href}?v=${Date.now()}`)).default;
  check('exports SimFlow plugin', plugin?.id === 'simflow' && typeof plugin.server === 'function');
  const hooks = await plugin.server({ directory: root, worktree: root });
  const existing = { hpc: { type: 'remote', url: 'https://example.invalid/mcp' } };
  const config = { mcp: existing, skills: { paths: [] } };
  await hooks.config(config);
  await hooks.config(config);
  check('adds canonical skills path once', config.skills.paths.filter(item => item === path.join(root, 'skills')).length === 1);
  check('preserves user MCP configuration', config.mcp === existing && Object.keys(config.mcp).length === 1 && config.mcp.hpc === existing.hpc);
  const empty = {};
  await hooks.config(empty);
  check('does not configure MCP by default', !('mcp' in empty));
}
function validatePackage(root) {
  const manifest = json(path.join(root, 'package.json'));
  check('package metadata and export', manifest.name === 'opencode-simflow' && manifest.version === json(path.join(ROOT, 'package.json')).version && manifest.exports?.['./server'] === './index.mjs');
  const actual = fs.readdirSync(path.join(root, 'skills')).filter(name => fs.existsSync(path.join(root, 'skills', name, 'SKILL.md')));
  check('package includes exactly 12 Skills', actual.length === SKILLS.length && actual.every(name => SKILLS.includes(name)));
  for (const name of ['mcp', 'runtime', 'workflow', 'schemas', '.mcp.json', '.claude.mcp.json', '.simflow', 'tests']) check(`package excludes ${name}`, !fs.existsSync(path.join(root, name)));
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'simflow-pack-'));
  try {
    const result = spawnSync('npm', ['pack', '--pack-destination', tmp], { cwd: root, encoding: 'utf8', env: { ...process.env, npm_config_cache: path.join(tmp, 'cache') }, timeout: 30000 });
    check('npm pack succeeds', result.status === 0, result.stderr || String(result.error || ''));
  } finally { fs.rmSync(tmp, { recursive: true, force: true }); }
}
async function main() {
  check('source loader exists', fs.existsSync(path.join(ROOT, '.opencode', 'plugins', 'simflow.js')));
  await validateAdapter(ROOT, path.join(ROOT, 'opencode', 'simflow.mjs'));
  if (BUILT) { const root = path.resolve(BUILT); validatePackage(root); await validateAdapter(root, path.join(root, 'index.mjs')); }
  console.log(`Errors: ${errors}`); process.exit(errors ? 1 : 0);
}
main().catch(error => { console.error(error); process.exit(1); });
