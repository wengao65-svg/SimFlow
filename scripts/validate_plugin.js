#!/usr/bin/env node
/**
 * Validate the SimFlow Codex plugin structure.
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const PLUGIN_PATH = path.join(ROOT, '.codex-plugin', 'plugin.json');
const MCP_PATH = path.join(ROOT, '.mcp.json');
const ROOT_MARKETPLACE_PATH = path.join(ROOT, '.agents', 'plugins', 'marketplace.json');
const WRAPPER_ROOT = process.env.SIMFLOW_MARKETPLACE_ROOT
  ? path.resolve(process.env.SIMFLOW_MARKETPLACE_ROOT)
  : null;
const WRAPPER_MARKETPLACE_PATH = WRAPPER_ROOT
  ? path.join(WRAPPER_ROOT, '.agents', 'plugins', 'marketplace.json')
  : null;
const WRAPPER_PLUGIN_PATH = WRAPPER_ROOT ? path.join(WRAPPER_ROOT, 'plugins', 'simflow') : null;
const SKILLS_LINK_PATH = path.join(ROOT, '.agents', 'skills');

const REQUIRED_FILES = [
  '.agents/plugins/marketplace.json',
  '.codex-plugin/plugin.json',
  '.codex/config.toml',
  '.mcp.json',
  'hooks/internal_workflow_hooks.json',
  'AGENTS.md',
  'package.json',
  'README.md',
  'scripts/start_mcp_server.py',
];

const REQUIRED_DIRS = [
  'skills',
  'agents',
  'workflow/stages',
  'workflow/workflows',
  'workflow/gates',
  'workflow/policies',
  'mcp',
  'mcp/servers',
  'runtime',
  'runtime/lib',
  'runtime/scripts',
  'schemas',
  'hooks',
  'notifications',
  'templates',
  'scripts',
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

function getMcpServers(mcp) {
  if (mcp && typeof mcp === 'object' && mcp.mcp_servers && typeof mcp.mcp_servers === 'object') {
    return mcp.mcp_servers;
  }
  if (mcp && typeof mcp === 'object' && mcp.mcpServers && typeof mcp.mcpServers === 'object') {
    return mcp.mcpServers;
  }
  return mcp && typeof mcp === 'object' ? mcp : {};
}

function isPlainObject(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function resolvePluginRelativePath(pluginRoot, relativePath) {
  return path.resolve(pluginRoot, relativePath);
}

function resolveMcpCwd(pluginRoot, server) {
  if (typeof server?.cwd !== 'string' || server.cwd.length === 0) {
    return pluginRoot;
  }
  if (path.isAbsolute(server.cwd)) {
    return server.cwd;
  }
  return resolvePluginRelativePath(pluginRoot, server.cwd);
}

function resolveMcpArgs(pluginRoot, server) {
  const args = Array.isArray(server?.args) ? [...server.args] : [];
  if (args.length === 0) {
    return args;
  }
  const first = args[0];
  if (typeof first === 'string' && first.startsWith('./')) {
    args[0] = resolvePluginRelativePath(pluginRoot, first);
  }
  return args;
}

function validateMcpStdio(name, server, pluginRoot) {
  if (!server || server.command !== 'python3' || !Array.isArray(server.args) || server.args.length === 0) {
    check(`${name} MCP stdio config is runnable`, false);
    return;
  }
  const input = [
    JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'simflow-validator', version: '0.1.0' },
      },
    }),
    JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} }),
    JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }),
    JSON.stringify({ jsonrpc: '2.0', id: 3, method: 'shutdown', params: {} }),
    '',
  ].join('\n');
  const commandArgs = resolveMcpArgs(pluginRoot, server);
  const commandCwd = resolveMcpCwd(pluginRoot, server);
  const result = spawnSync(server.command, commandArgs, {
    cwd: commandCwd,
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

function validatePluginRoot(label, pluginRoot) {
  check(`${label} exists`, fs.existsSync(pluginRoot));
  if (!fs.existsSync(pluginRoot)) {
    return;
  }
  const stat = fs.lstatSync(pluginRoot);
  check(`${label} is a real directory`, stat.isDirectory() && !stat.isSymbolicLink());
  check(`${label} has .codex-plugin/plugin.json`, fs.existsSync(path.join(pluginRoot, '.codex-plugin', 'plugin.json')));
  check(`${label} has .mcp.json`, fs.existsSync(path.join(pluginRoot, '.mcp.json')));
  check(`${label} has skills`, fs.existsSync(path.join(pluginRoot, 'skills', 'simflow', 'SKILL.md')));
  check(`${label} has mcp directory`, fs.existsSync(path.join(pluginRoot, 'mcp')));
  check(`${label} has runtime directory`, fs.existsSync(path.join(pluginRoot, 'runtime')));
  check(`${label} has scripts/start_mcp_server.py`, fs.existsSync(path.join(pluginRoot, 'scripts', 'start_mcp_server.py')));
}

function validateMarketplaceSourcePaths(marketplace, marketplaceRoot, label) {
  if (!Array.isArray(marketplace.plugins)) {
    return;
  }
  for (const pluginEntry of marketplace.plugins) {
    if (pluginEntry.source?.source !== 'local') {
      continue;
    }
    const sourcePath = pluginEntry.source?.path;
    const pluginName = pluginEntry.name || '<unnamed>';
    const hasSourcePath = typeof sourcePath === 'string' && sourcePath.trim().length > 0;
    check(`${label} ${pluginName} local source.path is not empty`, hasSourcePath);
    if (!hasSourcePath) {
      console.error('    Local marketplace entries must use the ./plugins/simflow wrapper path.');
      continue;
    }
    const normalizedSourcePath = sourcePath.trim();
    const resolvesToMarketplaceRoot = path.resolve(marketplaceRoot, normalizedSourcePath) === marketplaceRoot;
    const isRepositoryRootPath = normalizedSourcePath === './' || normalizedSourcePath === '.';
    check(
      `${label} ${pluginName} local source.path uses ./plugins/simflow wrapper`,
      !isRepositoryRootPath && !resolvesToMarketplaceRoot,
    );
    if (isRepositoryRootPath || resolvesToMarketplaceRoot) {
      console.error('    source.path: "./" is not accepted by current Codex CLI builds; use ./plugins/simflow in a wrapper marketplace.');
    }
  }
}

function validateMarketplace(marketplacePath, marketplaceRoot, expectedSourcePath, expectedPluginRoot, label, options = {}) {
  try {
    const marketplace = readJson(marketplacePath);
    console.log(`  ${label} root: ${marketplaceRoot}`);
    check(`${label} has name`, typeof marketplace.name === 'string' && marketplace.name.length > 0);
    const requiresSimflowPlugin = options.requiresSimflowPlugin !== false;
    check(
      `${label} has plugins array${requiresSimflowPlugin ? '' : ' (may be empty)'}`,
      Array.isArray(marketplace.plugins) && (requiresSimflowPlugin ? marketplace.plugins.length > 0 : true),
    );
    validateMarketplaceSourcePaths(marketplace, marketplaceRoot, label);

    const simflow = Array.isArray(marketplace.plugins)
      ? marketplace.plugins.find(pluginEntry => pluginEntry.name === 'simflow')
      : null;
    if (requiresSimflowPlugin) {
      check(`${label} includes simflow entry`, !!simflow);
    } else {
      check(`${label} does not expose simflow from the source repository root`, !simflow);
    }

    if (simflow) {
      check(`${label} simflow source is local`, simflow.source?.source === 'local');
      check(`${label} simflow path is ${expectedSourcePath}`, simflow.source?.path === expectedSourcePath);
      check(`${label} simflow has installation policy`, typeof simflow.policy?.installation === 'string' && simflow.policy.installation.length > 0);
      check(`${label} simflow has authentication policy`, typeof simflow.policy?.authentication === 'string' && simflow.policy.authentication.length > 0);
      check(`${label} simflow has category`, typeof simflow.category === 'string' && simflow.category.length > 0);

      if (simflow.source?.path === expectedSourcePath) {
        const resolved = path.resolve(marketplaceRoot, simflow.source.path);
        check(`${label} simflow path resolves to expected plugin root`, resolved === expectedPluginRoot);
        validatePluginRoot(`${label} plugin root`, resolved);
      }
    }
  } catch (error) {
    check(`${label} marketplace.json is valid JSON`, false);
  }
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
  check('plugin.json has author metadata', isPlainObject(plugin.author) && typeof plugin.author.name === 'string' && plugin.author.name.length > 0);
  check('plugin.json has license', typeof plugin.license === 'string' && plugin.license.length > 0);
  check('plugin.json has keywords', Array.isArray(plugin.keywords) && plugin.keywords.length > 0);
  check('plugin.json has interface block', isPlainObject(plugin.interface));
  check('plugin.json interface has displayName', typeof plugin.interface?.displayName === 'string' && plugin.interface.displayName.length > 0);
  check('plugin.json interface has shortDescription', typeof plugin.interface?.shortDescription === 'string' && plugin.interface.shortDescription.length > 0);
  check('plugin.json interface has category', typeof plugin.interface?.category === 'string' && plugin.interface.category.length > 0);
  check('plugin.json does not expose internal workflow hooks as Codex hooks', !('hooks' in plugin));

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
  const servers = getMcpServers(mcp);
  check('.mcp.json uses supported server map format', isPlainObject(servers));
  const serverNames = Object.keys(servers || {});
  check('.mcp.json registers exactly 7 SimFlow servers', serverNames.length === 7);
  serverNames.forEach(name => {
    const server = servers[name];
    check(`${name} uses python3 command`, server?.command === 'python3');
    check(`${name} uses MCP startup wrapper`, Array.isArray(server?.args) && server.args[0] === './scripts/start_mcp_server.py');
    check(`${name} passes server name to startup wrapper`, Array.isArray(server?.args) && server.args[1] === name);
    check(`${name} has plugin-root cwd`, server?.cwd === '.');
    if (Array.isArray(server?.args) && server.args.length > 0) {
      check(`${name} startup wrapper exists in source`, fs.existsSync(path.join(ROOT, server.args[0])));
    }
    validateMcpStdio(name, server, ROOT);
  });
  console.log(`  Found ${serverNames.length} MCP servers`);
} catch (error) {
  check('.mcp.json is valid JSON', false);
}

console.log('\n--- Root Marketplace ---');
validateMarketplace(ROOT_MARKETPLACE_PATH, ROOT, './plugins/simflow', path.join(ROOT, 'plugins', 'simflow'), 'root marketplace', {
  requiresSimflowPlugin: false,
});

if (WRAPPER_ROOT) {
  console.log('\n--- Optional Marketplace Wrapper ---');
  validateMarketplace(
    WRAPPER_MARKETPLACE_PATH,
    WRAPPER_ROOT,
    './plugins/simflow',
    WRAPPER_PLUGIN_PATH,
    'wrapper marketplace',
  );
}

console.log('\n--- Codex Hooks Separation ---');
check('internal workflow hook registry exists', existsWithinRoot('hooks/internal_workflow_hooks.json'));
check('Codex lifecycle hooks are not configured', !existsWithinRoot('hooks/hooks.json'));

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
