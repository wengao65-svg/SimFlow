#!/usr/bin/env node
/** Validate the Skill-only Claude Code source adapter and optional wrapper. */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const WRAPPER = process.env.SIMFLOW_CLAUDE_MARKETPLACE_ROOT;
const SKILLS = ['simflow-literature-review', 'simflow-reference-extraction', 'simflow-proposal', 'simflow-modeling', 'simflow-computation', 'simflow-analysis-visualization', 'simflow-writing', 'simflow-vasp', 'simflow-cp2k', 'simflow-lammps', 'simflow-gpumd', 'simflow-mlp'];
let errors = 0;
function check(label, value) { console.log(`  ${value ? 'OK' : 'ERROR'}: ${label}`); if (!value) errors++; }
function json(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
function validateSkills(root) {
  const dir = path.join(root, 'skills');
  check('skills directory exists', fs.existsSync(dir));
  if (!fs.existsSync(dir)) return;
  const actual = fs.readdirSync(dir).filter(name => fs.existsSync(path.join(dir, name, 'SKILL.md')));
  check('exactly 12 public Skills', actual.length === SKILLS.length && actual.every(name => SKILLS.includes(name)));
  for (const name of SKILLS) {
    const file = path.join(dir, name, 'SKILL.md');
    check(`${name} has SKILL.md`, fs.existsSync(file));
    if (fs.existsSync(file)) {
      const content = fs.readFileSync(file, 'utf8');
      check(`${name} has valid frontmatter`, content.startsWith('---\n') && content.includes(`\nname: ${name}\n`) && content.includes('\ndescription:') && content.includes('\n---\n'));
    }
  }
}
function validatePlugin(root, packaged = false) {
  const manifest = json(path.join(root, '.claude-plugin', 'plugin.json'));
  check('Claude plugin name and version', manifest.name === 'simflow' && !!manifest.version);
  check('Claude plugin has no MCP or hooks', !('mcpServers' in manifest) && !('hooks' in manifest));
  validateSkills(root);
  for (const name of ['.claude.mcp.json', '.mcp.json']) check(`excludes ${name}`, !fs.existsSync(path.join(root, name)));
  if (packaged) {
    for (const name of ['mcp', 'runtime', 'workflow', 'schemas', 'tests', '.simflow']) check(`package excludes ${name}`, !fs.existsSync(path.join(root, name)));
  }
}
validatePlugin(ROOT);
const rootMarketplace = json(path.join(ROOT, '.claude-plugin', 'marketplace.json'));
check('source marketplace includes SimFlow', rootMarketplace.plugins?.some(entry => entry.name === 'simflow'));
if (WRAPPER) {
  const wrapper = path.resolve(WRAPPER);
  const marketplace = json(path.join(wrapper, '.claude-plugin', 'marketplace.json'));
  const entry = marketplace.plugins?.find(item => item.name === 'simflow');
  check('wrapper marketplace points to copied plugin', entry?.source === './plugins/simflow');
  validatePlugin(path.join(wrapper, 'plugins', 'simflow'), true);
}
console.log(`Errors: ${errors}`);
process.exit(errors ? 1 : 0);
