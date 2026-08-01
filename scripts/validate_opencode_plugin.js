#!/usr/bin/env node
/** Validate the SimFlow OpenCode source adapter and generated npm package. */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const BUILT_ROOT = process.env.SIMFLOW_OPENCODE_PLUGIN_ROOT
  ? path.resolve(process.env.SIMFLOW_OPENCODE_PLUGIN_ROOT)
  : null;
const SERVER_NAMES = [
  'simflow_state', 'hpc',
];
const PACKAGED_SKILLS = [
  'simflow',
  'simflow-literature-review',
  'simflow-proposal',
  'simflow-modeling',
  'simflow-computation',
  'simflow-analysis-visualization',
  'simflow-writing',
  'simflow-safety-gates',
  'simflow-vasp',
  'simflow-qe',
  'simflow-cp2k',
  'simflow-lammps',
  'simflow-gpumd',
  'simflow-mlp',
  'simflow-gaussian',
  'simflow-checkpoint',
  'simflow-handoff',
  'simflow-verify',
];
const RESTRICTED_NAMES = new Set(['POTCAR', 'WAVECAR', 'CHGCAR', 'OUTCAR', 'vasprun.xml']);

let errors = 0;

function check(label, condition, detail = '') {
  if (condition) {
    console.log(`  OK: ${label}`);
    return;
  }
  console.error(`  ERROR: ${label}`);
  if (detail) console.error(String(detail).split('\n').map((line) => `    ${line}`).join('\n'));
  errors += 1;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

function npmCommand(args) {
  const candidates = [
    process.env.npm_execpath,
    ...String(process.env.PATH || '').split(path.delimiter).map((entry) => path.join(entry, 'npm')),
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      const resolved = fs.realpathSync(candidate);
      if (resolved.endsWith('.js')) return [process.execPath, [resolved, ...args]];
    } catch {
      // Try the next npm entry.
    }
  }
  return ['npm', args];
}

function findRestricted(root) {
  const findings = [];
  if (!fs.existsSync(root)) return findings;
  for (const entry of fs.readdirSync(root)) {
    const fullPath = path.join(root, entry);
    const stat = fs.lstatSync(fullPath);
    if (stat.isSymbolicLink()) continue;
    if (stat.isDirectory()) findings.push(...findRestricted(fullPath));
    else if (RESTRICTED_NAMES.has(entry)) findings.push(fullPath);
  }
  return findings;
}

function mcpInitialize(name, config, pluginRoot) {
  const input = [
    JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'opencode', version: '1.18.9' },
      },
    }),
    JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} }),
    JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }),
    JSON.stringify({ jsonrpc: '2.0', id: 3, method: 'shutdown', params: {} }),
    '',
  ].join('\n');
  const [command, ...args] = config.command;
  const result = spawnSync(command, args, {
    cwd: pluginRoot,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
    input,
    encoding: 'utf-8',
    timeout: 10000,
  });
  check(`${name} MCP exits cleanly`, result.status === 0, result.stderr || result.error);
  check(`${name} MCP has no startup stderr`, !(result.stderr || '').trim(), result.stderr);
  const responses = (result.stdout || '').trim().split('\n').filter(Boolean).map((line) => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter(Boolean);
  const initialize = responses.find((item) => item.id === 1)?.result;
  const tools = responses.find((item) => item.id === 2)?.result?.tools;
  check(`${name} MCP initialize response is valid`, initialize?.serverInfo?.name === name);
  check(`${name} MCP tools/list returns tools`, Array.isArray(tools) && tools.length > 0);
  if (name === 'simflow_state') {
    check('OpenCode MCP guidance uses the skill tool', initialize?.instructions?.includes('skill tool'));
    check('OpenCode MCP guidance preserves project_root requirement', initialize?.instructions?.includes('project_root'));
  }
}

async function loadPlugin(entry) {
  const moduleUrl = `${pathToFileURL(entry).href}?validate=${Date.now()}`;
  const pluginModule = await import(moduleUrl);
  check(`${entry} exports SimFlow plugin id`, pluginModule.default?.id === 'simflow');
  check(`${entry} exports server function`, typeof pluginModule.default?.server === 'function');
  return pluginModule.default;
}

async function validatePluginConfig(label, pluginRoot, entry) {
  console.log(`\n--- ${label} ---`);
  const plugin = await loadPlugin(entry);
  const hooks = await plugin.server({ directory: ROOT, worktree: ROOT });
  check(`${label} exposes config hook`, typeof hooks.config === 'function');

  const config = {};
  await hooks.config(config);
  const expectedSkills = path.join(pluginRoot, 'skills');
  check(`${label} injects canonical skills path`, config.skills?.paths?.includes(expectedSkills));
  check(`${label} injects exactly 2 MCP servers`, Object.keys(config.mcp || {}).length === SERVER_NAMES.length);
  for (const name of SERVER_NAMES) {
    const server = config.mcp?.[name];
    check(`${label} registers ${name}`, server?.type === 'local');
    check(`${label} ${name} uses absolute startup path`, path.isAbsolute(server?.command?.[1] || ''));
    check(`${label} ${name} passes server name`, server?.command?.[2] === name);
    check(`${label} ${name} remains enabled`, server?.enabled === true);
  }

  await hooks.config(config);
  check(`${label} skills injection is idempotent`, config.skills.paths.filter((item) => item === expectedSkills).length === 1);
  check(`${label} MCP injection is idempotent`, Object.keys(config.mcp).length === SERVER_NAMES.length);

  const existing = { type: 'remote', url: 'https://example.invalid/mcp' };
  const collision = { mcp: { hpc: existing } };
  await hooks.config(collision);
  check(`${label} preserves existing same-name MCP config`, collision.mcp.hpc === existing);

  const previousPython = process.env.SIMFLOW_PYTHON;
  process.env.SIMFLOW_PYTHON = '/custom/simflow-python';
  const overrideHooks = await plugin.server({ directory: ROOT, worktree: ROOT });
  const override = {};
  await overrideHooks.config(override);
  check(`${label} honors SIMFLOW_PYTHON`, override.mcp.simflow_state.command[0] === '/custom/simflow-python');
  if (previousPython === undefined) delete process.env.SIMFLOW_PYTHON;
  else process.env.SIMFLOW_PYTHON = previousPython;

  for (const name of SERVER_NAMES) mcpInitialize(name, config.mcp[name], pluginRoot);
}

function validateBuiltPackage(pluginRoot) {
  console.log('\n--- Built OpenCode Package ---');
  const manifest = readJson(path.join(pluginRoot, 'package.json'));
  const rootVersion = readJson(path.join(ROOT, 'package.json')).version;
  check('OpenCode package name is opencode-simflow', manifest.name === 'opencode-simflow');
  check('OpenCode package version matches project version', manifest.version === rootVersion);
  check('OpenCode package exposes ./server', manifest.exports?.['./server'] === './index.mjs');
  check('OpenCode package targets stable 1.18.9', manifest.engines?.opencode === '>=1.18.9 <2');
  for (const skill of PACKAGED_SKILLS) {
    check(`OpenCode package includes ${skill}`, fs.existsSync(path.join(pluginRoot, 'skills', skill, 'SKILL.md')));
  }
  for (const forbidden of ['tests', '.simflow', '.omx', '.codex-plugin', '.claude-plugin', '.mcp.json', '.claude.mcp.json']) {
    check(`OpenCode package excludes ${forbidden}`, !fs.existsSync(path.join(pluginRoot, forbidden)));
  }
  check('OpenCode package excludes restricted simulation artifacts', findRestricted(pluginRoot).length === 0);

  const packRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'simflow-opencode-pack-'));
  try {
    const [npmExecutable, npmArgs] = npmCommand(['pack', '--pack-destination', packRoot]);
    const packed = spawnSync(npmExecutable, npmArgs, {
      cwd: pluginRoot,
      env: { ...process.env, npm_config_cache: path.join(packRoot, 'cache') },
      encoding: 'utf-8',
      timeout: 30000,
    });
    const tarball = `${manifest.name.replace(/^@/, '').replace('/', '-')}-${manifest.version}.tgz`;
    check('OpenCode package npm pack succeeds', packed.status === 0 && fs.existsSync(path.join(packRoot, tarball)), packed.stderr || packed.error);
  } finally {
    fs.rmSync(packRoot, { recursive: true, force: true });
  }
  check('npm package manifest includes plugin entry', manifest.files.includes('index.mjs'));
  check('npm package manifest excludes workflow state', !manifest.files.includes('.simflow'));
}

async function main() {
  check('OpenCode local loader exists', fs.existsSync(path.join(ROOT, '.opencode', 'plugins', 'simflow.js')));
  check('OpenCode local loader forwards canonical module', fs.readFileSync(path.join(ROOT, '.opencode', 'plugins', 'simflow.js'), 'utf-8').includes('../../opencode/simflow.mjs'));
  await validatePluginConfig('Source OpenCode Plugin', ROOT, path.join(ROOT, 'opencode', 'simflow.mjs'));

  if (BUILT_ROOT) {
    validateBuiltPackage(BUILT_ROOT);
    await validatePluginConfig('Built OpenCode Plugin', BUILT_ROOT, path.join(BUILT_ROOT, 'index.mjs'));
  }

  console.log('\n--- Summary ---');
  if (errors > 0) {
    console.error(`Errors: ${errors}`);
    process.exit(1);
  }
  console.log('Errors: 0');
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
