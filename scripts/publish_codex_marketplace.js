#!/usr/bin/env node
/**
 * Publish dist/codex-marketplace to the codex-marketplace branch.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const DIST = path.join(ROOT, 'dist', 'codex-marketplace');
const BRANCH = process.env.SIMFLOW_CODEX_MARKETPLACE_BRANCH || 'codex-marketplace';
const REMOTE = process.env.SIMFLOW_CODEX_MARKETPLACE_REMOTE || 'origin';
const SKIP_BUILD = process.argv.includes('--no-build');
const DRY_RUN = process.argv.includes('--dry-run');
const EXCLUDED_NAMES = new Set([
  '.cache',
  '.omx',
  '.pytest_cache',
  '.simflow',
  '__pycache__',
  'cache',
  'dist',
  'node_modules',
  'tests',
]);

function isBlockedName(name) {
  const upper = name.toUpperCase();
  return upper === 'POTCAR' || upper.startsWith('POTCAR.');
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || ROOT,
    encoding: 'utf-8',
    stdio: options.capture ? 'pipe' : 'inherit',
  });
  if (result.status !== 0) {
    const stderr = result.stderr ? `\n${result.stderr}` : '';
    throw new Error(`${command} ${args.join(' ')} failed${stderr}`);
  }
  return result.stdout || '';
}

function copyRecursive(source, target) {
  const stat = fs.lstatSync(source);
  if (stat.isSymbolicLink()) {
    throw new Error(`Refusing to publish symlink: ${source}`);
  }
  if (stat.isDirectory()) {
    fs.mkdirSync(target, { recursive: true });
    for (const entry of fs.readdirSync(source)) {
      if (EXCLUDED_NAMES.has(entry) || entry.endsWith('.pyc') || isBlockedName(entry)) {
        continue;
      }
      copyRecursive(path.join(source, entry), path.join(target, entry));
    }
    return;
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
}

function emptyWorktree(worktree) {
  for (const entry of fs.readdirSync(worktree)) {
    if (entry === '.git') {
      continue;
    }
    fs.rmSync(path.join(worktree, entry), { recursive: true, force: true });
  }
}

function hasLocalBranch(branch) {
  const result = spawnSync('git', ['show-ref', '--verify', '--quiet', `refs/heads/${branch}`], { cwd: ROOT });
  return result.status === 0;
}

function hasRemoteBranch(remote, branch) {
  const result = spawnSync('git', ['ls-remote', '--exit-code', '--heads', remote, branch], { cwd: ROOT });
  return result.status === 0;
}

function ensureMarketplaceDist() {
  if (!SKIP_BUILD) {
    run('npm', ['run', 'build:codex-marketplace']);
  }
  const marketplace = path.join(DIST, '.agents', 'plugins', 'marketplace.json');
  const plugin = path.join(DIST, 'plugins', 'simflow', '.codex-plugin', 'plugin.json');
  if (!fs.existsSync(marketplace) || !fs.existsSync(plugin)) {
    throw new Error('dist/codex-marketplace is missing required marketplace files');
  }
}

function prepareWorktree(worktree) {
  if (hasLocalBranch(BRANCH)) {
    run('git', ['worktree', 'add', worktree, BRANCH]);
    return;
  }
  if (hasRemoteBranch(REMOTE, BRANCH)) {
    run('git', ['fetch', REMOTE, `${BRANCH}:${BRANCH}`]);
    run('git', ['worktree', 'add', worktree, BRANCH]);
    return;
  }
  run('git', ['worktree', 'add', '--detach', worktree, 'HEAD']);
  run('git', ['switch', '--orphan', BRANCH], { cwd: worktree });
}

function publish() {
  ensureMarketplaceDist();
  const worktree = fs.mkdtempSync(path.join(os.tmpdir(), 'simflow-codex-marketplace-'));
  try {
    prepareWorktree(worktree);
    emptyWorktree(worktree);
    copyRecursive(DIST, worktree);
    run('git', ['add', '-A'], { cwd: worktree });
    const status = run('git', ['status', '--short'], { cwd: worktree, capture: true }).trim();
    if (!status) {
      console.log(`${BRANCH} is already up to date.`);
      return;
    }
    const version = JSON.parse(fs.readFileSync(path.join(DIST, 'plugins', 'simflow', '.codex-plugin', 'plugin.json'), 'utf-8')).version;
    run('git', ['commit', '-m', `Publish SimFlow Codex marketplace ${version}`], { cwd: worktree });
    if (DRY_RUN) {
      console.log(`Dry run complete. ${BRANCH} commit was created in ${worktree} but not pushed.`);
      return;
    }
    run('git', ['push', REMOTE, `HEAD:${BRANCH}`], { cwd: worktree });
    console.log(`Published ${DIST} to ${REMOTE}/${BRANCH}`);
  } finally {
    if (!DRY_RUN) {
      spawnSync('git', ['worktree', 'remove', '--force', worktree], { cwd: ROOT, stdio: 'ignore' });
      fs.rmSync(worktree, { recursive: true, force: true });
    }
  }
}

publish();
