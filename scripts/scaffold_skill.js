#!/usr/bin/env node
/**
 * Scaffold a new SimFlow skill.
 * Usage: node scaffold_skill.js <skill-name> [--description "description"]
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SKILLS_DIR = path.join(ROOT, 'skills');

const args = process.argv.slice(2);
const skillName = args[0];

if (!skillName) {
  console.error('Usage: node scaffold_skill.js <skill-name> [--description "description"]');
  process.exit(1);
}

const descIdx = args.indexOf('--description');
const description = descIdx >= 0 && args[descIdx + 1] ? args[descIdx + 1] : '';

const skillDir = path.join(SKILLS_DIR, skillName);
if (fs.existsSync(skillDir)) {
  console.error(`Skill already exists: ${skillName}`);
  process.exit(1);
}

// Create directories
fs.mkdirSync(path.join(skillDir, 'scripts'), { recursive: true });
fs.mkdirSync(path.join(skillDir, 'references'), { recursive: true });
fs.mkdirSync(path.join(skillDir, 'assets'), { recursive: true });

// Create SKILL.md
const template = `# ${skillName} — ${description || 'New Skill'}

## 触发条件

- TODO: 描述触发此 skill 的条件

## 输入条件

- TODO: 列出必需输入

## 输出 Artifact

- TODO: 列出产出 artifact

## 状态写入规则

- TODO: 描述状态写入规则

## Checkpoint 规则

- TODO: 描述 checkpoint 策略

## 禁止事项

- TODO: 列出禁止事项

## 需要人工确认的场景

- TODO: 列出需要人工确认的场景
`;

fs.writeFileSync(path.join(skillDir, 'SKILL.md'), template);

console.log(`Skill created: ${skillName}`);
console.log(`  Directory: ${skillDir}`);
console.log(`  SKILL.md: ${path.join(skillDir, 'SKILL.md')}`);
