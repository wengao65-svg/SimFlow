#!/usr/bin/env node

const { guardRoots } = require('./marketplace_version_guard');

function main() {
  const [currentRoot, previousRoot] = process.argv.slice(2);
  if (!currentRoot || !previousRoot) {
    console.error('Usage: node scripts/check_marketplace_version_guard.js <current-plugin-root> <previous-plugin-root>');
    process.exit(2);
  }

  const { current, previous, result } = guardRoots(currentRoot, previousRoot);
  if (!result.ok) {
    const added = result.diff.added.length ? ` added: ${result.diff.added.join(', ')}` : '';
    const removed = result.diff.removed.length ? ` removed: ${result.diff.removed.join(', ')}` : '';
    console.error(
      `plugin version must increase when packaged skills change; ` +
      `current=${current.version}, previous=${previous.version};${added}${removed}`,
    );
    process.exit(1);
  }

  console.log('marketplace packaged skill/version guard passed');
}

main();
