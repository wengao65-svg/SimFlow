#!/usr/bin/env node
/**
 * Validate all SKILL.md files for required sections.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SKILLS_DIR = path.join(ROOT, 'skills');

const REQUIRED_SECTIONS = [
  '## 触发条件',
  '## 输入条件',
  '## 输出 Artifact',
  '## 状态写入规则',
  '## Checkpoint 规则',
  '## 禁止事项',
  '## 需要人工确认的场景',
];

let errors = 0;
let warnings = 0;

console.log('=== SimFlow Skills Validation ===\n');

const skillDirs = fs.readdirSync(SKILLS_DIR).filter(d =>
  fs.existsSync(path.join(SKILLS_DIR, d, 'SKILL.md'))
);

console.log(`Found ${skillDirs.length} skills\n`);

skillDirs.forEach(skillName => {
  const skillFile = path.join(SKILLS_DIR, skillName, 'SKILL.md');
  const content = fs.readFileSync(skillFile, 'utf-8');
  const missing = REQUIRED_SECTIONS.filter(s => !content.includes(s));

  if (missing.length > 0) {
    console.error(`  ERROR: ${skillName} - missing sections: ${missing.join(', ')}`);
    errors++;
  } else {
    console.log(`  OK: ${skillName}`);
  }

  // Check for non-empty content
  if (content.trim().split('\n').length < 10) {
    console.warn(`  WARNING: ${skillName} - content seems too short`);
    warnings++;
  }
});

console.log(`\n=== Summary ===`);
console.log(`Errors: ${errors}`);
console.log(`Warnings: ${warnings}`);
process.exit(errors > 0 ? 1 : 0);
