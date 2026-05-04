#!/usr/bin/env node
/**
 * Validate all SKILL.md files for Codex metadata and SimFlow sections.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SKILLS_DIR = path.join(ROOT, 'skills');

const REQUIRED_SECTION_GROUPS = [
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

let errors = 0;
let warnings = 0;

function parseFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n*/);
  if (!match) {
    return null;
  }

  const fields = {};
  for (const line of match[1].split('\n')) {
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
    body: content.slice(match[0].length),
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

  const missingSections = REQUIRED_SECTION_GROUPS
    .filter(group => !group.options.some(option => body.includes(option)))
    .map(group => group.label);

  if (missingSections.length > 0) {
    console.error(`  ERROR: ${skillName} - missing sections: ${missingSections.join(', ')}`);
    errors++;
  } else {
    console.log(`  OK: ${skillName}`);
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
