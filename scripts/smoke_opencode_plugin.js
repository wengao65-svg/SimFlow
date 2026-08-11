#!/usr/bin/env node
/** Run an isolated OpenCode install/config/skill/MCP smoke test. */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const PACKAGE_ROOT = path.resolve(process.argv[2] || path.join(ROOT, 'dist', 'opencode-plugin'));
const OPENCODE = process.env.SIMFLOW_OPENCODE_BIN || 'opencode';
const SERVER_NAMES = [
  'simflow_state', 'hpc',
];
const SKILL_NAMES = [
  'simflow', 'simflow-literature-review', 'simflow-proposal', 'simflow-modeling',
  'simflow-computation', 'simflow-analysis-visualization', 'simflow-writing',
  'simflow-vasp', 'simflow-cp2k', 'simflow-lammps', 'simflow-gpumd',
  'simflow-mlp',
];

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || ROOT,
    env: options.env || process.env,
    encoding: 'utf-8',
    timeout: options.timeout || 60000,
  });
  if (result.status !== 0) {
    const output = [result.stdout, result.stderr, result.error?.message].filter(Boolean).join('\n');
    throw new Error(`${command} ${args.join(' ')} failed\n${output}`);
  }
  return `${result.stdout || ''}${result.stderr || ''}`;
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

function runNpm(args, options = {}) {
  const [command, commandArgs] = npmCommand(args);
  return run(command, commandArgs, options);
}

function isSupportedOpenCodeVersion(value) {
  const match = String(value).trim().match(/^v?(\d+)\.(\d+)\.(\d+)(?:\+[0-9A-Za-z.-]+)?$/);
  if (!match) return false;
  const [, major, minor, patch] = match.map(Number);
  return major === 1 && (minor > 18 || (minor === 18 && patch >= 9));
}

function main() {
  if (!fs.existsSync(path.join(PACKAGE_ROOT, 'package.json'))) {
    throw new Error(`OpenCode package is missing: ${PACKAGE_ROOT}`);
  }

  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'simflow-opencode-smoke-'));
  try {
    const packDir = path.join(tempRoot, 'pack');
    const npmCache = path.join(tempRoot, 'npm-cache');
    const configHome = path.join(tempRoot, 'config');
    const opencodeConfig = path.join(configHome, 'opencode');
    const project = path.join(tempRoot, 'project');
    fs.mkdirSync(packDir, { recursive: true });
    fs.mkdirSync(opencodeConfig, { recursive: true });
    fs.mkdirSync(project, { recursive: true });

    const npmEnv = { ...process.env, npm_config_cache: npmCache };
    runNpm(['pack', '--pack-destination', packDir], {
      cwd: PACKAGE_ROOT,
      env: npmEnv,
    });
    const manifest = JSON.parse(fs.readFileSync(path.join(PACKAGE_ROOT, 'package.json'), 'utf-8'));
    const tarballName = `${manifest.name.replace(/^@/, '').replace('/', '-')}-${manifest.version}.tgz`;
    const tarball = path.join(packDir, tarballName);
    if (!fs.existsSync(tarball)) throw new Error(`npm pack did not create ${tarballName}`);

    const pluginUrl = pathToFileURL(path.join(PACKAGE_ROOT, 'index.mjs')).href;
    fs.writeFileSync(path.join(opencodeConfig, 'opencode.json'), `${JSON.stringify({
      $schema: 'https://opencode.ai/config.json',
      autoupdate: false,
      plugin: [pluginUrl],
    }, null, 2)}\n`);

    const isolatedEnv = {
      ...process.env,
      HOME: path.join(tempRoot, 'home'),
      XDG_CONFIG_HOME: configHome,
      XDG_DATA_HOME: path.join(tempRoot, 'data'),
      XDG_STATE_HOME: path.join(tempRoot, 'state'),
      XDG_CACHE_HOME: path.join(tempRoot, 'cache'),
      PYTHONDONTWRITEBYTECODE: '1',
      OPENCODE_DISABLE_MODELS_FETCH: '1',
      OPENCODE_DISABLE_AUTOUPDATE: '1',
    };

    const version = run(OPENCODE, ['--version'], { cwd: project, env: isolatedEnv }).trim();
    if (!isSupportedOpenCodeVersion(version)) {
      throw new Error(`Expected stable OpenCode >=1.18.9 <2 for smoke test, found ${version}`);
    }

    const configOutput = run(OPENCODE, ['debug', 'config'], { cwd: project, env: isolatedEnv });
    if (!configOutput.includes(pluginUrl)) {
      throw new Error(`Resolved OpenCode config did not load ${pluginUrl}\n${configOutput.slice(0, 6000)}`);
    }

    const skillOutput = run(OPENCODE, ['debug', 'skill'], { cwd: project, env: isolatedEnv });
    for (const name of SKILL_NAMES) {
      if (!skillOutput.includes(name)) {
        throw new Error(`OpenCode skill discovery is missing ${name}\n${skillOutput.slice(0, 6000)}`);
      }
    }

    const mcpOutput = run(OPENCODE, ['mcp', 'list'], { cwd: project, env: isolatedEnv, timeout: 90000 });
    for (const name of SERVER_NAMES) {
      if (!mcpOutput.includes(name)) {
        throw new Error(`OpenCode MCP status is missing ${name}\n${mcpOutput.slice(0, 6000)}`);
      }
    }

    console.log(`OpenCode ${version} isolated smoke passed`);
    console.log(`Skills discovered: ${SKILL_NAMES.length}`);
    console.log(`MCP servers discovered: ${SERVER_NAMES.length}`);
  } finally {
    fs.rmSync(tempRoot, { recursive: true, force: true });
  }
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    console.error(error.stack || error.message);
    process.exit(1);
  }
}

module.exports = { isSupportedOpenCodeVersion };
