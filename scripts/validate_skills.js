#!/usr/bin/env node
/**
 * Validate all SKILL.md files for Codex metadata and SimFlow sections.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SKILLS_DIR = path.join(ROOT, 'skills');

const LEGACY_REQUIRED_SECTION_GROUPS = [
  {
    label: 'trigger conditions',
    options: ['## 触发条件', '## Trigger conditions'],
  },
  {
    label: 'input conditions',
    options: ['## 输入条件', '## Input conditions'],
  },
  {
    label: 'output artifacts',
    options: ['## 输出 Artifact', '## Output artifacts'],
  },
  {
    label: 'status write rules',
    options: ['## 状态写入规则', '## Status write rules'],
  },
  {
    label: 'checkpoint rules',
    options: ['## Checkpoint 规则', '## Checkpoint rules'],
  },
  {
    label: 'prohibited actions',
    options: ['## 禁止事项', '## Prohibited actions'],
  },
  {
    label: 'manual confirmation scenarios',
    options: ['## 需要人工确认的场景', '## Manual confirmation scenarios'],
  },
];

const PURE_SKILL_REQUIRED_SECTIONS = [
  '## Purpose',
  '## Use when',
  '## Do not use when',
  '## Task principles',
  '## Minimum checks',
  '## Common failure modes',
  '## Escalate uncertainty when',
  '## Completion criteria',
  '## Optional references',
];

const RESEARCH_TASK_SKILLS = new Set([
  'simflow-literature-review',
  'simflow-proposal',
  'simflow-modeling',
  'simflow-computation',
  'simflow-analysis-visualization',
  'simflow-writing',
]);

const DOMAIN_SKILLS = new Set([
  'simflow-vasp',
  'simflow-cp2k',
  'simflow-lammps',
  'simflow-gpumd',
  'simflow-mlp',
]);

const PURE_DOMAIN_REQUIRED_SECTIONS = [
  '## Purpose',
  '## Use when',
  '## Do not use when',
  '## Domain principles',
  '## Minimum checks',
  '## Common failure modes',
  '## Escalate uncertainty when',
  '## Completion criteria',
  '## Optional references',
];

const ROUTER_REQUIRED_SECTIONS = [
  '## Purpose',
  '## Use when',
  '## Routing model',
  '## Selection rules',
  '## Runtime escalation',
  '## Ambiguous intent',
  '## Prohibited actions',
  '## Completion criteria',
];

const FORBIDDEN_TASK_RUNTIME_PATTERNS = [
  /project_reentry/i,
  /start_activity/i,
  /finish_activity/i,
  /begin_experiment/i,
  /session_handoff/i,
  /required mcp engagement/i,
  /register(?:ed|ing)?\s+(?:an\s+)?artifact/i,
  /create(?:s|d|ing)?\s+(?:a\s+)?checkpoint/i,
  /update_stage/i,
  /\.simflow\/state/i,
];

let errors = 0;
let warnings = 0;

function parseFrontmatter(content) {
  const lines = content.split(/\r?\n/);
  if (lines[0] !== '---' || /^---\s+name:/.test(lines[0])) {
    return null;
  }
  const closeIndex = lines.findIndex((line, index) => index > 0 && line === '---');
  if (closeIndex === -1) {
    return null;
  }

  const fields = {};
  for (const line of lines.slice(1, closeIndex)) {
    const separator = line.indexOf(':');
    if (separator === -1) {
      continue;
    }
    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim();
    fields[key] = value;
  }

  return {
    fields,
    body: lines.slice(closeIndex + 1).join('\n'),
  };
}

console.log('=== SimFlow Skills Validation ===\n');

const skillDirs = fs.readdirSync(SKILLS_DIR).filter(dir =>
  fs.existsSync(path.join(SKILLS_DIR, dir, 'SKILL.md'))
);

console.log(`Found ${skillDirs.length} skills\n`);

skillDirs.forEach(skillName => {
  const skillFile = path.join(SKILLS_DIR, skillName, 'SKILL.md');
  const content = fs.readFileSync(skillFile, 'utf-8');
  const parsed = parseFrontmatter(content);

  if (!parsed) {
    console.error(`  ERROR: ${skillName} - missing frontmatter`);
    errors++;
    return;
  }

  const { fields, body } = parsed;
  const missingFields = ['name', 'description'].filter(field => !fields[field]);
  if (missingFields.length > 0) {
    console.error(`  ERROR: ${skillName} - missing frontmatter fields: ${missingFields.join(', ')}`);
    errors++;
  }

  if (fields.name && fields.name !== skillName) {
    console.error(`  ERROR: ${skillName} - frontmatter name must match directory name`);
    errors++;
  }

  const isResearchTask = RESEARCH_TASK_SKILLS.has(skillName);
  const isDomain = DOMAIN_SKILLS.has(skillName);
  const isRouter = skillName === 'simflow';
  const missingSections = isResearchTask
    ? PURE_SKILL_REQUIRED_SECTIONS.filter(section => !body.includes(section))
    : isDomain
      ? PURE_DOMAIN_REQUIRED_SECTIONS.filter(section => !body.includes(section))
    : isRouter
      ? ROUTER_REQUIRED_SECTIONS.filter(section => !body.includes(section))
      : LEGACY_REQUIRED_SECTION_GROUPS
      .filter(group => !group.options.some(option => body.includes(option)))
      .map(group => group.label);

  if (missingSections.length > 0) {
    console.error(`  ERROR: ${skillName} - missing sections: ${missingSections.join(', ')}`);
    errors++;
  } else {
    console.log(`  OK: ${skillName}`);
  }

  if (isResearchTask || isDomain) {
    for (const pattern of FORBIDDEN_TASK_RUNTIME_PATTERNS) {
      if (pattern.test(body)) {
        console.error(`  ERROR: ${skillName} - pure task skill contains runtime directive matching ${pattern}`);
        errors++;
      }
    }
  }

  if (!body.includes('# ')) {
    console.warn(`  WARNING: ${skillName} - missing top-level heading`);
    warnings++;
  }

  if (body.trim().split('\n').length < 10) {
    console.warn(`  WARNING: ${skillName} - content seems too short`);
    warnings++;
  }
});

console.log('\n=== Summary ===');
console.log(`Errors: ${errors}`);
console.log(`Warnings: ${warnings}`);
process.exit(errors > 0 ? 1 : 0);
