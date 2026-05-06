#!/usr/bin/env node
/**
 * Build the stable local Codex marketplace wrapper and register it with Codex.
 */

const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const DEFAULT_WRAPPER = path.join(process.env.HOME || process.cwd(), '.cache', 'simflow', 'codex-marketplace');
const WRAPPER_ROOT = path.resolve(process.argv[2] || process.env.SIMFLOW_MARKETPLACE_ROOT || DEFAULT_WRAPPER);

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: ROOT,
    stdio: 'inherit',
    ...options,
  });
  return result.status === null ? 1 : result.status;
}

const buildStatus = run(process.execPath, [path.join(ROOT, 'scripts', 'build_marketplace_wrapper.js'), WRAPPER_ROOT]);
if (buildStatus !== 0) {
  process.exit(buildStatus);
}

run('codex', ['plugin', 'marketplace', 'remove', 'simflow-local']);

const addStatus = run('codex', ['plugin', 'marketplace', 'add', WRAPPER_ROOT]);
if (addStatus !== 0) {
  console.error(`Failed to add Codex marketplace wrapper: ${WRAPPER_ROOT}`);
  process.exit(addStatus);
}

console.log(`Registered SimFlow Codex marketplace wrapper: ${WRAPPER_ROOT}`);
