#!/usr/bin/env node
/**
 * Build the Claude Code marketplace wrapper for SimFlow.
 *
 * The wrapper uses the official Claude Code marketplace shape:
 *   <wrapper>/.claude-plugin/marketplace.json
 *   <wrapper>/plugins/simflow/
 *
 * plugins/simflow is a real copied plugin directory, never a symlink.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DEFAULT_WRAPPER = path.join(ROOT, 'dist', 'claude-marketplace');
const args = process.argv.slice(2);
const wrapperArg = args.find(arg => !arg.startsWith('--'));
const nameArg = args.find(arg => arg.startsWith('--marketplace-name='));
const MARKETPLACE_NAME = (nameArg ? nameArg.split('=')[1] : process.env.SIMFLOW_CLAUDE_MARKETPLACE_NAME) || 'simflow-claude-marketplace';
const WRAPPER_ROOT = path.resolve(wrapperArg || DEFAULT_WRAPPER);
const PLUGIN_ROOT = path.join(WRAPPER_ROOT, 'plugins', 'simflow');
const MARKETPLACE_PATH = path.join(WRAPPER_ROOT, '.claude-plugin', 'marketplace.json');

const REQUIRED_ENTRIES = [
  { source: '.claude-plugin/plugin.json', target: '.claude-plugin/plugin.json' },
  { source: '.claude.mcp.json', target: '.claude.mcp.json' },
  { source: 'skills', target: 'skills' },
  { source: 'agents', target: 'agents' },
  { source: 'mcp', target: 'mcp' },
  { source: 'runtime', target: 'runtime' },
  { source: 'schemas', target: 'schemas' },
  { source: 'templates', target: 'templates' },
  { source: 'workflow', target: 'workflow' },
  { source: 'scripts/start_mcp_server.py', target: 'scripts/start_mcp_server.py' },
  { source: 'docs/quickstart_claude.md', target: 'docs/quickstart_claude.md' },
  { source: 'docs/release_claude.md', target: 'docs/release_claude.md' },
  { source: 'docs/state-and-checkpoint.md', target: 'docs/state-and-checkpoint.md' },
  { source: 'docs/installation.md', target: 'docs/installation.md' },
  { source: 'docs/user_guide.md', target: 'docs/user_guide.md' },
  { source: 'docs/mcp-design.md', target: 'docs/mcp-design.md' },
  { source: 'docs/skill-design.md', target: 'docs/skill-design.md' },
  { source: 'docs/credentials-policy.md', target: 'docs/credentials-policy.md' },
  { source: 'AGENTS.md', target: 'AGENTS.md' },
  { source: 'README.md', target: 'README.md' },
  { source: 'LICENSE', target: 'LICENSE' },
];

const EXCLUDED_NAMES = new Set([
  '.git',
  '.git-data',
  '.github',
  '.simflow',
  '.omx',
  '.pytest_cache',
  '.mypy_cache',
  '__pycache__',
  'node_modules',
  'plugins',
  'dist',
  '.cache',
  'cache',
  'tests',
]);

function isBlockedName(name) {
  const upper = name.toUpperCase();
  return upper === 'POTCAR' || upper.startsWith('POTCAR.');
}

function copyRecursive(source, target) {
  const stat = fs.lstatSync(source);
  if (stat.isSymbolicLink()) {
    throw new Error(`Refusing to copy symlink into Claude marketplace wrapper: ${source}`);
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

function writeJson(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(`${filePath}.tmp`, `${JSON.stringify(data, null, 2)}\n`);
  fs.renameSync(`${filePath}.tmp`, filePath);
}

function parseSkillFrontmatter(content, skillName) {
  const lines = content.split(/\r?\n/);
  if (lines[0] !== '---') {
    throw new Error(`${skillName} SKILL.md must start with a standalone --- frontmatter delimiter`);
  }
  if (/^---\s+name:/.test(lines[0])) {
    throw new Error(`${skillName} SKILL.md uses single-line frontmatter`);
  }
  const closeIndex = lines.findIndex((line, index) => index > 0 && line === '---');
  if (closeIndex === -1) {
    throw new Error(`${skillName} SKILL.md is missing a standalone closing --- frontmatter delimiter`);
  }
  const fields = {};
  for (const line of lines.slice(1, closeIndex)) {
    const separator = line.indexOf(':');
    if (separator === -1) {
      continue;
    }
    fields[line.slice(0, separator).trim()] = line.slice(separator + 1).trim();
  }
  if (!fields.name) {
    throw new Error(`${skillName} SKILL.md frontmatter name must not be empty`);
  }
  if (fields.name !== skillName) {
    throw new Error(`${skillName} SKILL.md frontmatter name must match its directory`);
  }
  if (!fields.description) {
    throw new Error(`${skillName} SKILL.md frontmatter description must not be empty`);
  }
}

function validateSkillCopies() {
  const sourceSkillsDir = path.join(ROOT, 'skills');
  const targetSkillsDir = path.join(PLUGIN_ROOT, 'skills');
  const skillNames = fs.readdirSync(sourceSkillsDir)
    .filter(skillName => fs.existsSync(path.join(sourceSkillsDir, skillName, 'SKILL.md')));
  for (const skillName of skillNames) {
    const sourceSkill = path.join(sourceSkillsDir, skillName, 'SKILL.md');
    const targetSkill = path.join(targetSkillsDir, skillName, 'SKILL.md');
    if (!fs.existsSync(targetSkill)) {
      throw new Error(`Built Claude plugin is missing ${skillName}/SKILL.md`);
    }
    const sourceContent = fs.readFileSync(sourceSkill);
    const targetContent = fs.readFileSync(targetSkill);
    if (!sourceContent.equals(targetContent)) {
      throw new Error(`${skillName}/SKILL.md changed during Claude marketplace wrapper build`);
    }
    parseSkillFrontmatter(targetContent.toString('utf-8'), skillName);
  }
}

function build() {
  fs.mkdirSync(path.dirname(PLUGIN_ROOT), { recursive: true });
  fs.rmSync(PLUGIN_ROOT, { recursive: true, force: true });
  fs.mkdirSync(PLUGIN_ROOT, { recursive: true });

  for (const entry of REQUIRED_ENTRIES) {
    const source = path.join(ROOT, entry.source);
    if (!fs.existsSync(source)) {
      continue;
    }
    copyRecursive(source, path.join(PLUGIN_ROOT, entry.target));
  }

  const marketplace = {
    name: MARKETPLACE_NAME,
    description: 'Claude Code marketplace wrapper for SimFlow.',
    owner: {
      name: 'SimFlow Maintainers',
      email: 'maintainers@example.com',
    },
    plugins: [
      {
        name: 'simflow',
        source: './plugins/simflow',
        description: 'Claude Code computational simulation workflows for dry-run-first DFT, AIMD, and MD research.',
        author: {
          name: 'SimFlow Maintainers',
          email: 'maintainers@example.com',
        },
        strict: true,
      },
    ],
  };
  writeJson(MARKETPLACE_PATH, marketplace);

  const pluginStat = fs.lstatSync(PLUGIN_ROOT);
  if (!pluginStat.isDirectory() || pluginStat.isSymbolicLink()) {
    throw new Error(`${PLUGIN_ROOT} must be a real directory`);
  }
  if (!fs.existsSync(path.join(PLUGIN_ROOT, '.claude-plugin', 'plugin.json'))) {
    throw new Error('Built Claude plugin is missing .claude-plugin/plugin.json');
  }
  if (!fs.existsSync(path.join(PLUGIN_ROOT, '.claude.mcp.json'))) {
    throw new Error('Built Claude plugin is missing .claude.mcp.json');
  }
  if (!fs.existsSync(path.join(PLUGIN_ROOT, 'scripts', 'start_mcp_server.py'))) {
    throw new Error('Built Claude plugin is missing scripts/start_mcp_server.py');
  }
  if (fs.existsSync(path.join(PLUGIN_ROOT, 'tests'))) {
    throw new Error('Built Claude plugin must not contain tests');
  }
  validateSkillCopies();
  console.log(`Built SimFlow Claude marketplace wrapper at ${WRAPPER_ROOT}`);
}

build();
