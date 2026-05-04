#!/usr/bin/env node
/**
 * Validate the SimFlow Codex plugin structure.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PLUGIN_PATH = path.join(ROOT, '.codex-plugin', 'plugin.json');
const MCP_PATH = path.join(ROOT, '.mcp.json');
const MARKETPLACE_PATH = path.join(ROOT, '.agents', 'plugins', 'marketplace.json');
const SKILLS_LINK_PATH = path.join(ROOT, '.agents', 'skills');

const REQUIRED_FILES = [
  '.codex-plugin/plugin.json',
  '.codex/config.toml',
  '.mcp.json',
  '.agents/plugins/marketplace.json',
  'hooks/internal_workflow_hooks.json',
  'AGENTS.md',
  'package.json',
  'README.md',
];

const REQUIRED_DIRS = [
  'skills',
  'agents',
  'workflow/stages',
  'workflow/workflows',
  'workflow/gates',
  'workflow/policies',
  'mcp/servers',
  'runtime/lib',
  'runtime/scripts',
  'schemas',
  'hooks',
  'notifications',
  'templates',
];

const REQUIRED_STAGES = [
  'literature', 'review', 'proposal', 'modeling',
  'input_generation', 'compute', 'analysis', 'visualization', 'writing',
];

const REQUIRED_WORKFLOWS = ['dft', 'aimd', 'md'];
const LEGACY_MANIFEST_FIELDS = [
  'skills_path',
  'mcp_config',
  'agents_path',
  'workflow_path',
  'runtime_path',
  'schemas_path',
  'templates_path',
  'permissions',
  'entry_points',
  'state_directory',
  'type',
];

let errors = 0;
let warnings = 0;

function check(label, condition, isWarning = false) {
  if (!condition) {
    if (isWarning) {
      console.warn(`  WARNING: ${label}`);
      warnings++;
    } else {
      console.error(`  ERROR: ${label}`);
      errors++;
    }
  } else {
    console.log(`  OK: ${label}`);
  }
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

function existsWithinRoot(relativePath) {
  return fs.existsSync(path.join(ROOT, relativePath));
}

console.log('=== SimFlow Codex Plugin Validation ===\n');

console.log('--- Required Files ---');
REQUIRED_FILES.forEach(file => {
  check(file, existsWithinRoot(file));
});

console.log('\n--- Required Directories ---');
REQUIRED_DIRS.forEach(dir => {
  check(dir, existsWithinRoot(dir));
});

console.log('\n--- Plugin Manifest ---');
let plugin;
try {
  plugin = readJson(PLUGIN_PATH);
  check('plugin.json has name', typeof plugin.name === 'string' && plugin.name.length > 0);
  check('plugin.json has version', typeof plugin.version === 'string' && plugin.version.length > 0);
  check('plugin.json has description', typeof plugin.description === 'string' && plugin.description.length > 0);
  check('plugin.json has skills path', typeof plugin.skills === 'string' && plugin.skills.startsWith('./'));
  check('plugin.json has MCP path', typeof plugin.mcpServers === 'string' && plugin.mcpServers.startsWith('./'));

  if (typeof plugin.skills === 'string' && plugin.skills.startsWith('./')) {
    const skillsPath = path.join(ROOT, plugin.skills);
    check('plugin.json skills path exists', fs.existsSync(skillsPath));
  }

  if (typeof plugin.mcpServers === 'string' && plugin.mcpServers.startsWith('./')) {
    const mcpPath = path.join(ROOT, plugin.mcpServers);
    check('plugin.json MCP path exists', fs.existsSync(mcpPath));
  }

  LEGACY_MANIFEST_FIELDS.forEach(field => {
    check(`plugin.json omits legacy field ${field}`, !(field in plugin));
  });
} catch (error) {
  check('plugin.json is valid JSON', false);
}

console.log('\n--- Root MCP Configuration ---');
try {
  const mcp = readJson(MCP_PATH);
  check('.mcp.json has mcpServers', !!mcp.mcpServers && typeof mcp.mcpServers === 'object');
  const serverNames = Object.keys(mcp.mcpServers || {});
  check('.mcp.json registers at least 7 servers', serverNames.length >= 7);
  console.log(`  Found ${serverNames.length} MCP servers`);
} catch (error) {
  check('.mcp.json is valid JSON', false);
}

console.log('\n--- Marketplace ---');
try {
  const marketplace = readJson(MARKETPLACE_PATH);
  check('marketplace has name', typeof marketplace.name === 'string' && marketplace.name.length > 0);
  check('marketplace has plugins array', Array.isArray(marketplace.plugins) && marketplace.plugins.length > 0);

  const simflow = Array.isArray(marketplace.plugins)
    ? marketplace.plugins.find(pluginEntry => pluginEntry.name === 'simflow')
    : null;
  check('marketplace includes simflow entry', !!simflow);

  if (simflow) {
    check('simflow source is local', simflow.source?.source === 'local');
    check('simflow path is ./-prefixed', typeof simflow.source?.path === 'string' && simflow.source.path.startsWith('./'));
    check('simflow has installation policy', typeof simflow.policy?.installation === 'string' && simflow.policy.installation.length > 0);
    check('simflow has authentication policy', typeof simflow.policy?.authentication === 'string' && simflow.policy.authentication.length > 0);
    check('simflow has category', typeof simflow.category === 'string' && simflow.category.length > 0);

    if (typeof simflow.source?.path === 'string' && simflow.source.path.startsWith('./')) {
      const resolved = path.resolve(path.dirname(MARKETPLACE_PATH), simflow.source.path);
      check('simflow marketplace path exists', fs.existsSync(resolved));
    }
  }
} catch (error) {
  check('marketplace.json is valid JSON', false);
}

console.log('\n--- Skills Discovery Layer ---');
try {
  const stat = fs.lstatSync(SKILLS_LINK_PATH);
  check('.agents/skills exists', true);
  check('.agents/skills is directory or symlink', stat.isDirectory() || stat.isSymbolicLink());
} catch (error) {
  check('.agents/skills exists', false);
}

console.log('\n--- Stage Definitions ---');
REQUIRED_STAGES.forEach(stage => {
  check(`stages/${stage}.json`, existsWithinRoot(path.join('workflow/stages', `${stage}.json`)));
});

console.log('\n--- Workflow Definitions ---');
REQUIRED_WORKFLOWS.forEach(workflow => {
  check(`workflows/${workflow}.json`, existsWithinRoot(path.join('workflow/workflows', `${workflow}.json`)));
});

console.log('\n=== Summary ===');
console.log(`Errors: ${errors}`);
console.log(`Warnings: ${warnings}`);
process.exit(errors > 0 ? 1 : 0);
