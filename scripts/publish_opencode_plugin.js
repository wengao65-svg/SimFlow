#!/usr/bin/env node
/** Publish the generated OpenCode npm package after release validation. */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const DIST = path.join(ROOT, 'dist', 'opencode-plugin');
const SKIP_BUILD = process.argv.includes('--no-build');
const DRY_RUN = process.argv.includes('--dry-run');

function run(command, args) {
  const result = spawnSync(command, args, { cwd: ROOT, stdio: 'inherit' });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

if (!SKIP_BUILD) {
  run('npm', ['run', 'build:opencode-plugin']);
}
if (!fs.existsSync(path.join(DIST, 'package.json'))) {
  console.error('dist/opencode-plugin/package.json is missing');
  process.exit(1);
}

const args = ['publish', DIST, '--access', 'public'];
if (DRY_RUN) args.push('--dry-run');
run('npm', args);
