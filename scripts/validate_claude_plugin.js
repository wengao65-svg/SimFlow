#!/usr/bin/env node
/**
 * Validate the SimFlow Claude Code plugin adapter.
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const PLUGIN_PATH = path.join(ROOT, '.claude-plugin', 'plugin.json');
const MARKETPLACE_PATH = path.join(ROOT, '.claude-plugin', 'marketplace.json');
const CLAUDE_MCP_PATH = path.join(ROOT, '.claude.mcp.json');
const WRAPPER_ROOT = process.env.SIMFLOW_CLAUDE_MARKETPLACE_ROOT
  ? path.resolve(process.env.SIMFLOW_CLAUDE_MARKETPLACE_ROOT)
  : null;
const WRAPPER_MARKETPLACE_PATH = WRAPPER_ROOT
  ? path.join(WRAPPER_ROOT, '.claude-plugin', 'marketplace.json')
  : null;
const WRAPPER_PLUGIN_PATH = WRAPPER_ROOT ? path.join(WRAPPER_ROOT, 'plugins', 'simflow') : null;

const REQUIRED_FILES = [
  '.claude-plugin/plugin.json',
  '.claude-plugin/marketplace.json',
  '.claude.mcp.json',
  'scripts/start_mcp_server.py',
  'skills/simflow/SKILL.md',
  'AGENTS.md',
  'README.md',
  'package.json',
];

const REQUIRED_DIRS = [
  'skills',
  'agents',
  'workflow',
  'mcp',
  'runtime',
  'schemas',
  'templates',
  'scripts',
];

const SERVER_NAMES = [
  'simflow_state',
  'artifact_store',
  'checkpoint_store',
  'literature',
  'structure',
  'hpc',
  'parsers',
];

const FORBIDDEN_MARKETPLACE_COMPONENT_FIELDS = [
  'skills',
  'commands',
  'agents',
  'hooks',
  'mcpServers',
  'lspServers',
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

function isPlainObject(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function existsWithinRoot(relativePath) {
  return fs.existsSync(path.join(ROOT, relativePath));
}

function substituteClaudePluginRoot(value, pluginRoot) {
  if (typeof value !== 'string') {
    return value;
  }
  return value.replace(/\$\{CLAUDE_PLUGIN_ROOT\}/g, pluginRoot);
}

function validateMcpStdio(name, server, pluginRoot) {
  const input = [
    JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'simflow-claude-validator', version: '0.1.0' },
      },
    }),
    JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} }),
    JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }),
    JSON.stringify({ jsonrpc: '2.0', id: 3, method: 'shutdown', params: {} }),
    '',
  ].join('\n');

  const commandArgs = Array.isArray(server.args)
    ? server.args.map(arg => substituteClaudePluginRoot(arg, pluginRoot))
    : [];
  const commandCwd = substituteClaudePluginRoot(server.cwd || '${CLAUDE_PLUGIN_ROOT}', pluginRoot);
  const result = spawnSync(server.command, commandArgs, {
    cwd: commandCwd,
    env: {
      ...process.env,
      CLAUDE_PLUGIN_ROOT: pluginRoot,
      PYTHONDONTWRITEBYTECODE: '1',
    },
    input,
    encoding: 'utf-8',
    timeout: 5000,
  });
  const stderr = (result.stderr || '').trim();
  check(`${name} MCP stdio has no startup stderr`, stderr.length === 0);
  if (stderr) {
    console.error(stderr.split('\n').map(line => `    ${line}`).join('\n'));
  }
  const lines = (result.stdout || '').trim().split('\n').filter(Boolean);
  let initializeOk = false;
  let toolsOk = false;
  for (const line of lines) {
    try {
      const response = JSON.parse(line);
      if (response.id === 1 && response.result?.serverInfo?.name === name) {
        initializeOk = true;
      }
      if (response.id === 2 && Array.isArray(response.result?.tools) && response.result.tools.length > 0) {
        toolsOk = true;
      }
    } catch (_error) {
      // Handled by checks below.
    }
  }
  check(`${name} MCP initialize response is valid`, initializeOk);
  check(`${name} MCP tools/list returns tools`, toolsOk);
}

function validateClaudeMcpConfig(label, pluginRoot, mcpPath) {
  try {
    const mcp = readJson(mcpPath);
    check(`${label} has top-level mcpServers`, isPlainObject(mcp.mcpServers));
    const servers = mcp.mcpServers || {};
    const names = Object.keys(servers);
    check(`${label} registers exactly 7 SimFlow servers`, names.length === SERVER_NAMES.length);
    SERVER_NAMES.forEach(name => {
      const server = servers[name];
      check(`${label} registers ${name}`, isPlainObject(server));
      if (!isPlainObject(server)) {
        return;
      }
      check(`${label} ${name} uses python3 command`, server.command === 'python3');
      check(
        `${label} ${name} uses CLAUDE_PLUGIN_ROOT startup wrapper`,
        Array.isArray(server.args) && server.args[0] === '${CLAUDE_PLUGIN_ROOT}/scripts/start_mcp_server.py',
      );
      check(`${label} ${name} passes server name`, Array.isArray(server.args) && server.args[1] === name);
      check(`${label} ${name} uses CLAUDE_PLUGIN_ROOT cwd`, server.cwd === '${CLAUDE_PLUGIN_ROOT}');
      validateMcpStdio(name, server, pluginRoot);
    });
  } catch (error) {
    check(`${label} is valid JSON`, false);
  }
}

function parseSkillFrontmatter(content) {
  const lines = content.split(/\r?\n/);
  const result = {
    fields: {},
    firstLineOk: lines[0] === '---',
    singleLineFrontmatter: /^---\s+name:/.test(lines[0] || ''),
    hasClosingDelimiter: false,
  };
  const closeIndex = lines.findIndex((line, index) => index > 0 && line === '---');
  if (closeIndex === -1) {
    return result;
  }
  result.hasClosingDelimiter = true;
  for (const line of lines.slice(1, closeIndex)) {
    const separator = line.indexOf(':');
    if (separator === -1) {
      continue;
    }
    result.fields[line.slice(0, separator).trim()] = line.slice(separator + 1).trim();
  }
  return result;
}

function validateSkillFrontmatterDirectory(label, skillsDir) {
  check(`${label} skills directory exists`, fs.existsSync(skillsDir));
  if (!fs.existsSync(skillsDir)) {
    return;
  }
  const skillNames = fs.readdirSync(skillsDir)
    .filter(skillName => fs.existsSync(path.join(skillsDir, skillName, 'SKILL.md')));
  check(`${label} has bundled skills`, skillNames.length > 0);
  skillNames.forEach(skillName => {
    const skillFile = path.join(skillsDir, skillName, 'SKILL.md');
    const content = fs.readFileSync(skillFile, 'utf-8');
    const parsed = parseSkillFrontmatter(content);
    check(`${label} ${skillName} frontmatter starts with standalone ---`, parsed.firstLineOk);
    check(`${label} ${skillName} does not use single-line frontmatter`, !parsed.singleLineFrontmatter);
    check(`${label} ${skillName} frontmatter has standalone closing ---`, parsed.hasClosingDelimiter);
    check(`${label} ${skillName} frontmatter name is non-empty`, typeof parsed.fields.name === 'string' && parsed.fields.name.length > 0);
    check(`${label} ${skillName} frontmatter description is non-empty`, typeof parsed.fields.description === 'string' && parsed.fields.description.length > 0);
    check(`${label} ${skillName} frontmatter name matches directory`, parsed.fields.name === skillName);
  });
}

function validateClaudeManifest(label, pluginPath) {
  try {
    const plugin = readJson(pluginPath);
    check(`${label} plugin.json has name`, typeof plugin.name === 'string' && plugin.name.length > 0);
    check(`${label} plugin.json has version`, typeof plugin.version === 'string' && plugin.version.length > 0);
    check(`${label} plugin.json has description`, typeof plugin.description === 'string' && plugin.description.length > 0);
    check(`${label} plugin.json has author metadata`, isPlainObject(plugin.author) && typeof plugin.author.name === 'string' && plugin.author.name.length > 0);
    check(`${label} plugin.json has license`, typeof plugin.license === 'string' && plugin.license.length > 0);
    check(`${label} plugin.json has keywords`, Array.isArray(plugin.keywords) && plugin.keywords.length > 0);
    check(`${label} plugin.json points to Claude MCP config`, plugin.mcpServers === './.claude.mcp.json');
    check(`${label} plugin.json does not configure hooks`, !('hooks' in plugin));
    check(`${label} plugin.json does not use Codex interface block`, !('interface' in plugin));
  } catch (error) {
    check(`${label} plugin.json is valid JSON`, false);
  }
}

function validateMarketplace(marketplacePath, marketplaceRoot, expectedSource, expectedPluginRoot, label) {
  try {
    const marketplace = readJson(marketplacePath);
    console.log(`  ${label} root: ${marketplaceRoot}`);
    check(`${label} has name`, typeof marketplace.name === 'string' && marketplace.name.length > 0);
    check(`${label} has owner name`, typeof marketplace.owner?.name === 'string' && marketplace.owner.name.length > 0);
    check(`${label} has plugins array`, Array.isArray(marketplace.plugins) && marketplace.plugins.length > 0);
    const simflow = Array.isArray(marketplace.plugins)
      ? marketplace.plugins.find(pluginEntry => pluginEntry.name === 'simflow')
      : null;
    check(`${label} includes simflow entry`, !!simflow);
    if (!simflow) {
      return;
    }
    check(`${label} simflow source is ${expectedSource}`, simflow.source === expectedSource);
    check(`${label} simflow marketplace entry does not duplicate plugin version`, !('version' in simflow));
    check(`${label} simflow strict mode enabled`, simflow.strict === true);
    FORBIDDEN_MARKETPLACE_COMPONENT_FIELDS.forEach(field => {
      check(`${label} simflow marketplace entry does not define ${field}`, !(field in simflow));
    });
    if (simflow.source === expectedSource) {
      const resolved = path.resolve(marketplaceRoot, simflow.source);
      check(`${label} simflow source resolves to expected plugin root`, resolved === expectedPluginRoot);
    }
  } catch (error) {
    check(`${label} marketplace.json is valid JSON`, false);
  }
}

function validatePluginRoot(label, pluginRoot) {
  check(`${label} exists`, fs.existsSync(pluginRoot));
  if (!fs.existsSync(pluginRoot)) {
    return;
  }
  const stat = fs.lstatSync(pluginRoot);
  check(`${label} is a real directory`, stat.isDirectory() && !stat.isSymbolicLink());
  check(`${label} has .claude-plugin/plugin.json`, fs.existsSync(path.join(pluginRoot, '.claude-plugin', 'plugin.json')));
  check(`${label} has .claude.mcp.json`, fs.existsSync(path.join(pluginRoot, '.claude.mcp.json')));
  check(`${label} has skills`, fs.existsSync(path.join(pluginRoot, 'skills', 'simflow', 'SKILL.md')));
  check(`${label} has agents directory`, fs.existsSync(path.join(pluginRoot, 'agents')));
  check(`${label} has mcp directory`, fs.existsSync(path.join(pluginRoot, 'mcp')));
  check(`${label} has runtime directory`, fs.existsSync(path.join(pluginRoot, 'runtime')));
  check(`${label} has scripts/start_mcp_server.py`, fs.existsSync(path.join(pluginRoot, 'scripts', 'start_mcp_server.py')));
  check(`${label} excludes tests`, !fs.existsSync(path.join(pluginRoot, 'tests')));
  check(`${label} excludes .simflow`, !fs.existsSync(path.join(pluginRoot, '.simflow')));
  check(`${label} excludes .omx`, !fs.existsSync(path.join(pluginRoot, '.omx')));
  validateClaudeManifest(label, path.join(pluginRoot, '.claude-plugin', 'plugin.json'));
  validateClaudeMcpConfig(`${label} .claude.mcp.json`, pluginRoot, path.join(pluginRoot, '.claude.mcp.json'));
  validateSkillFrontmatterDirectory(label, path.join(pluginRoot, 'skills'));
}

console.log('=== SimFlow Claude Plugin Validation ===\n');

console.log('--- Required Files ---');
REQUIRED_FILES.forEach(file => {
  check(file, existsWithinRoot(file));
});

console.log('\n--- Required Directories ---');
REQUIRED_DIRS.forEach(dir => {
  check(dir, existsWithinRoot(dir));
});

console.log('\n--- Claude Plugin Manifest ---');
validateClaudeManifest('root Claude plugin', PLUGIN_PATH);

console.log('\n--- Claude MCP Configuration ---');
validateClaudeMcpConfig('root .claude.mcp.json', ROOT, CLAUDE_MCP_PATH);

console.log('\n--- Claude Marketplace ---');
validateMarketplace(MARKETPLACE_PATH, ROOT, './', ROOT, 'root Claude marketplace');

console.log('\n--- Root Skill Frontmatter ---');
validateSkillFrontmatterDirectory('root Claude plugin', path.join(ROOT, 'skills'));

console.log('\n--- Codex Separation ---');
check('Codex plugin manifest still exists', fs.existsSync(path.join(ROOT, '.codex-plugin', 'plugin.json')));
check('Codex root marketplace still exists', fs.existsSync(path.join(ROOT, '.agents', 'plugins', 'marketplace.json')));
check('Claude adapter does not replace Codex MCP config', fs.existsSync(path.join(ROOT, '.mcp.json')) && fs.existsSync(CLAUDE_MCP_PATH));

if (WRAPPER_ROOT) {
  console.log('\n--- Optional Claude Marketplace Wrapper ---');
  validateMarketplace(
    WRAPPER_MARKETPLACE_PATH,
    WRAPPER_ROOT,
    './plugins/simflow',
    WRAPPER_PLUGIN_PATH,
    'wrapper Claude marketplace',
  );
  validatePluginRoot('wrapper Claude plugin root', WRAPPER_PLUGIN_PATH);
}

console.log('\n=== Summary ===');
console.log(`Errors: ${errors}`);
console.log(`Warnings: ${warnings}`);
process.exit(errors > 0 ? 1 : 0);
