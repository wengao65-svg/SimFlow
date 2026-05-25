#!/usr/bin/env node
/**
 * Generate lightweight SimFlow release notes from local Git metadata.
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');

const args = process.argv.slice(2);
const sinceArg = args.find(arg => arg.startsWith('--since='));
const untilArg = args.find(arg => arg.startsWith('--until='));
const since = sinceArg ? sinceArg.split('=')[1] : process.env.SIMFLOW_RELEASE_NOTES_SINCE || '';
const until = untilArg ? untilArg.split('=')[1] : process.env.SIMFLOW_RELEASE_NOTES_UNTIL || 'HEAD';

function run(command, commandArgs) {
  const result = spawnSync(command, commandArgs, {
    encoding: 'utf-8',
    stdio: 'pipe',
  });
  if (result.status !== 0) {
    const details = [result.stdout, result.stderr].filter(Boolean).join('\n').trim();
    throw new Error(`${command} ${commandArgs.join(' ')} failed${details ? `\n${details}` : ''}`);
  }
  return result.stdout.trim();
}

function gitLogRange() {
  if (since) {
    return `${since}..${until}`;
  }
  return until;
}

function main() {
  const head = run('git', ['rev-parse', '--short', until]);
  const version = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf-8')).version;
  const logOutput = run('git', ['log', '--oneline', '--no-decorate', gitLogRange()]);
  const commits = logOutput ? logOutput.split(/\r?\n/) : [];
  const lines = [
    '# SimFlow Release Notes',
    '',
    `Version: ${version}`,
    `Target commit: ${head}`,
    '',
    '## Release Gates',
    '',
    '- Run `npm run validate:release` from a clean source tree.',
    '- Run manual Codex and Claude install smoke checks from `docs/release-checklist.md` before announcing.',
    '- Stop release work if restricted scientific artifacts are found in source, wrapper, or history checks.',
    '',
    '## Commits',
    '',
  ];
  if (commits.length === 0) {
    lines.push('- No commits in selected range.');
  } else {
    for (const commit of commits) {
      lines.push(`- ${commit}`);
    }
  }
  lines.push('');
  process.stdout.write(lines.join('\n'));
}

main();
