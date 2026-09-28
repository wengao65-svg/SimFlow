#!/usr/bin/env node
/** Validate the Codex Skill-only source plugin and optional marketplace wrapper. */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const WRAPPER = process.env.SIMFLOW_MARKETPLACE_ROOT;
const SKILLS = new Set(['simflow-literature-review', 'simflow-reference-extraction', 'simflow-proposal', 'simflow-modeling', 'simflow-computation', 'simflow-analysis-visualization', 'simflow-writing', 'simflow-vasp', 'simflow-cp2k', 'simflow-lammps', 'simflow-gpumd', 'simflow-mlp']);
const RETIRED = ['mcp', 'runtime', 'workflow', 'schemas', '.mcp.json', '.claude.mcp.json'];
let errors = 0;
function check(label, condition) { console.log(`  ${condition ? 'OK' : 'ERROR'}: ${label}`); if (!condition) errors++; }
function json(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
function validatePlugin(root, packaged = false) {
  const manifestPath = path.join(root, '.codex-plugin', 'plugin.json');
  check('Codex manifest exists', fs.existsSync(manifestPath));
  if (!fs.existsSync(manifestPath)) return;
  const manifest = json(manifestPath);
  check('Codex manifest name and version', manifest.name === 'simflow' && !!manifest.version);
  check('Codex manifest exposes Skills only', manifest.skills === './skills/' && !('mcpServers' in manifest) && !('hooks' in manifest) && !('permissions' in manifest));
  const dir = path.join(root, 'skills');
  check('Skills directory exists', fs.existsSync(dir));
  if (!fs.existsSync(dir)) return;
  const actual = fs.readdirSync(dir).filter(item => fs.existsSync(path.join(dir, item, 'SKILL.md')));
  check('exactly 12 public Skills', actual.length === SKILLS.size && actual.every(item => SKILLS.has(item)));
  for (const name of actual) {
    const body = fs.readFileSync(path.join(dir, name, 'SKILL.md'), 'utf8');
    check(`${name} frontmatter`, body.startsWith('---\n') && body.includes(`\nname: ${name}\n`) && body.includes('\ndescription:') && body.includes('\n---\n'));
  }
  for (const name of ['.mcp.json', '.claude.mcp.json']) check(`excludes ${name}`, !fs.existsSync(path.join(root, name)));
  if (packaged) {
    for (const name of RETIRED) check(`package excludes ${name}`, !fs.existsSync(path.join(root, name)));
    const forbidden = new Set(['POTCAR', 'WAVECAR', 'CHGCAR', 'OUTCAR', 'vasprun.xml']);
    const pending = [root]; let restricted = false;
    while (pending.length) {
      const current = pending.pop();
      for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
        if (forbidden.has(entry.name)) restricted = true;
        if (entry.isDirectory()) pending.push(path.join(current, entry.name));
      }
    }
    check('package excludes restricted VASP artifacts', !restricted);
  }
}
console.log('=== SimFlow Codex Skill Pack Validation ===');
validatePlugin(ROOT);
const rootMarketplace = json(path.join(ROOT, '.agents', 'plugins', 'marketplace.json'));
check('source marketplace does not expose repository root', Array.isArray(rootMarketplace.plugins) && !rootMarketplace.plugins.some(item => item.name === 'simflow'));
if (WRAPPER) {
  const wrapper = path.resolve(WRAPPER);
  const marketplace = json(path.join(wrapper, '.agents', 'plugins', 'marketplace.json'));
  const entry = marketplace.plugins?.find(item => item.name === 'simflow');
  check('wrapper marketplace points to copied plugin', entry?.source?.path === './plugins/simflow');
  validatePlugin(path.join(wrapper, 'plugins', 'simflow'), true);
}
console.log(`Errors: ${errors}`);
process.exit(errors ? 1 : 0);
