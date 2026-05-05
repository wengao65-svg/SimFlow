#!/usr/bin/env node
/**
 * Build the external Codex marketplace wrapper for local SimFlow installs.
 *
 * The wrapper uses the official marketplace shape:
 *   <wrapper>/.agents/plugins/marketplace.json
 *   <wrapper>/plugins/simflow/
 *
 * plugins/simflow is a real copied plugin directory, never a symlink.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DEFAULT_WRAPPER = '/home/gaofeng/test/SimFlow-marketplace';
const WRAPPER_ROOT = path.resolve(process.argv[2] || DEFAULT_WRAPPER);
const PLUGIN_ROOT = path.join(WRAPPER_ROOT, 'plugins', 'simflow');
const MARKETPLACE_PATH = path.join(WRAPPER_ROOT, '.agents', 'plugins', 'marketplace.json');

const REQUIRED_ENTRIES = [
  '.codex-plugin',
  'skills',
  '.mcp.json',
  'mcp',
  'runtime',
  'schemas',
  'templates',
  'workflow',
  'hooks',
  'notifications',
  'docs',
  'scripts',
  'AGENTS.md',
  'README.md',
  'LICENSE',
  'package.json',
  'pyproject.toml',
];

const EXCLUDED_NAMES = new Set([
  '.git',
  '.git-data',
  '.simflow',
  '.pytest_cache',
  '__pycache__',
  'node_modules',
  'plugins',
]);

function copyRecursive(source, target) {
  const stat = fs.lstatSync(source);
  if (stat.isSymbolicLink()) {
    throw new Error(`Refusing to copy symlink into plugin wrapper: ${source}`);
  }
  if (stat.isDirectory()) {
    fs.mkdirSync(target, { recursive: true });
    for (const entry of fs.readdirSync(source)) {
      if (EXCLUDED_NAMES.has(entry) || entry.endsWith('.pyc')) {
        continue;
      }
      copyRecursive(path.join(source, entry), path.join(target, entry));
    }
    return;
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
}

function writeJson(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(`${filePath}.tmp`, `${JSON.stringify(data, null, 2)}\n`);
  fs.renameSync(`${filePath}.tmp`, filePath);
}

function build() {
  fs.mkdirSync(path.dirname(PLUGIN_ROOT), { recursive: true });
  fs.rmSync(PLUGIN_ROOT, { recursive: true, force: true });
  fs.mkdirSync(PLUGIN_ROOT, { recursive: true });

  for (const entry of REQUIRED_ENTRIES) {
    const source = path.join(ROOT, entry);
    if (!fs.existsSync(source)) {
      continue;
    }
    copyRecursive(source, path.join(PLUGIN_ROOT, entry));
  }

  const marketplace = {
    name: 'simflow-local',
    interface: {
      displayName: 'SimFlow Local Plugins',
    },
    plugins: [
      {
        name: 'simflow',
        source: {
          source: 'local',
          path: './plugins/simflow',
        },
        policy: {
          installation: 'AVAILABLE',
          authentication: 'ON_INSTALL',
        },
        category: 'Productivity',
      },
    ],
  };
  writeJson(MARKETPLACE_PATH, marketplace);

  const pluginStat = fs.lstatSync(PLUGIN_ROOT);
  if (!pluginStat.isDirectory() || pluginStat.isSymbolicLink()) {
    throw new Error(`${PLUGIN_ROOT} must be a real directory`);
  }
  if (!fs.existsSync(path.join(PLUGIN_ROOT, '.codex-plugin', 'plugin.json'))) {
    throw new Error('Built plugin is missing .codex-plugin/plugin.json');
  }
  console.log(`Built SimFlow marketplace wrapper at ${WRAPPER_ROOT}`);
}

build();
