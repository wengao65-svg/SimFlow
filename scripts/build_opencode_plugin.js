#!/usr/bin/env node
/** Build the publishable OpenCode npm package for SimFlow. */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const OUTPUT = path.resolve(process.argv[2] || path.join(ROOT, 'dist', 'opencode-plugin'));
const PACKAGE_NAME = 'opencode-simflow';

const REQUIRED_ENTRIES = [
  ['skills', 'skills'],
  ['mcp', 'mcp'],
  ['runtime', 'runtime'],
  ['schemas', 'schemas'],
  ['templates', 'templates'],
  ['workflow', 'workflow'],
  ['scripts/start_mcp_server.py', 'scripts/start_mcp_server.py'],
  ['docs/quickstart_opencode.md', 'docs/quickstart_opencode.md'],
  ['docs/state-and-checkpoint.md', 'docs/state-and-checkpoint.md'],
  ['docs/installation.md', 'docs/installation.md'],
  ['docs/user_guide.md', 'docs/user_guide.md'],
  ['docs/mcp-design.md', 'docs/mcp-design.md'],
  ['docs/skill-design.md', 'docs/skill-design.md'],
  ['docs/credentials-policy.md', 'docs/credentials-policy.md'],
  ['AGENTS.md', 'AGENTS.md'],
  ['README.md', 'README.md'],
  ['LICENSE', 'LICENSE'],
];

const PACKAGED_SKILLS = new Set([
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
]);

const EXCLUDED_NAMES = new Set([
  '.git', '.github', '.simflow', '.omx', '.pytest_cache', '.mypy_cache',
  '__pycache__', 'node_modules', 'plugins', 'dist', '.cache', 'cache', 'tests',
]);

const REMOVED_PATHS = new Set([
  'workflow/stages/literature.json',
  'workflow/stages/review.json',
  'workflow/stages/input_generation.json',
  'workflow/stages/compute.json',
  'workflow/stages/analysis.json',
  'workflow/stages/visualization.json',
]);

function toPosix(relativePath) {
  return relativePath.split(path.sep).join('/').replace(/^\.\//, '');
}

function isBlockedName(name) {
  const upper = name.toUpperCase();
  return upper === 'POTCAR' || (upper.startsWith('POTCAR.') && upper !== 'POTCAR.METADATA.JSON');
}

function isExcluded(relativePath) {
  const normalized = toPosix(relativePath);
  if (REMOVED_PATHS.has(normalized)) return true;
  if (normalized === 'workflow/workflows' || normalized.startsWith('workflow/workflows/')) return true;
  if (normalized === 'runtime/scripts' || normalized.startsWith('runtime/scripts/')) return true;
  if (normalized.startsWith('skills/')) {
    const skillName = normalized.split('/')[1];
    if (skillName && !PACKAGED_SKILLS.has(skillName)) return true;
  }
  return false;
}

function copyRecursive(source, target, relativePath = '') {
  if (isExcluded(relativePath)) return;
  const stat = fs.lstatSync(source);
  if (stat.isSymbolicLink()) {
    throw new Error(`Refusing to copy symlink into OpenCode package: ${source}`);
  }
  if (stat.isDirectory()) {
    fs.mkdirSync(target, { recursive: true });
    for (const entry of fs.readdirSync(source)) {
      if (EXCLUDED_NAMES.has(entry) || entry.endsWith('.pyc') || isBlockedName(entry)) continue;
      copyRecursive(path.join(source, entry), path.join(target, entry), path.join(relativePath, entry));
    }
    return;
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

function validateSkills() {
  const skills = fs.readdirSync(path.join(OUTPUT, 'skills'))
    .filter((name) => fs.existsSync(path.join(OUTPUT, 'skills', name, 'SKILL.md')));
  const unexpected = skills.filter((name) => !PACKAGED_SKILLS.has(name));
  const missing = [...PACKAGED_SKILLS].filter((name) => !skills.includes(name));
  if (unexpected.length || missing.length) {
    throw new Error(`OpenCode skill surface mismatch; missing=${missing.join(',')} unexpected=${unexpected.join(',')}`);
  }
}

function build() {
  const rootPackage = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf-8'));
  fs.rmSync(OUTPUT, { recursive: true, force: true });
  fs.mkdirSync(OUTPUT, { recursive: true });

  fs.copyFileSync(path.join(ROOT, 'opencode', 'simflow.mjs'), path.join(OUTPUT, 'index.mjs'));
  for (const [source, target] of REQUIRED_ENTRIES) {
    const sourcePath = path.join(ROOT, source);
    if (fs.existsSync(sourcePath)) {
      copyRecursive(sourcePath, path.join(OUTPUT, target), target);
    }
  }

  writeJson(path.join(OUTPUT, 'package.json'), {
    name: PACKAGE_NAME,
    version: rootPackage.version,
    description: 'SimFlow computational simulation workflow layer for OpenCode.',
    type: 'module',
    main: './index.mjs',
    exports: {
      '.': './index.mjs',
      './server': './index.mjs',
    },
    files: [
      'index.mjs', 'skills', 'mcp', 'runtime', 'schemas', 'templates', 'workflow',
      'scripts', 'docs', 'AGENTS.md', 'README.md', 'LICENSE',
    ],
    engines: {
      node: '>=18',
      opencode: '>=1.18.9 <2',
      python: '>=3.10',
    },
    os: ['linux', 'darwin'],
    keywords: ['opencode', 'simulation', 'dft', 'molecular-dynamics', 'mcp', 'skills'],
    repository: {
      type: 'git',
      url: 'git+https://github.com/wengao65-svg/SimFlow.git',
    },
    homepage: 'https://github.com/wengao65-svg/SimFlow',
    bugs: 'https://github.com/wengao65-svg/SimFlow/issues',
    author: 'wengao65-svg',
    license: 'MIT',
  });

  validateSkills();
  console.log(`Built SimFlow OpenCode package at ${OUTPUT}`);
}

build();
