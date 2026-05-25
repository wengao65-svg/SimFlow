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
const template = `---
name: ${skillName}
description: ${description || 'Describe when this SimFlow skill should be used.'}
---

# ${skillName} — ${description || 'Workflow-layer Skill'}

## 触发条件

- TODO: 描述触发此 skill 的用户意图或研究阶段

## 输入条件

- TODO: 列出可接受的输入、已有 artifact、用户提供文件或 checkpoint

## 输出 Artifact

- TODO: 列出最低 evidence/artifact 要求
- TODO: 说明脚本、输入、输出、环境和 lineage 如何记录

## 状态写入规则

- 写入必须使用显式 project_root 下的 \`.simflow/\`
- 不要从 plugin root、MCP cwd 或 \`.omx/\` 推断 workflow state

## Checkpoint 规则

- TODO: 描述阶段边界、失败恢复或人工交接时的 checkpoint 策略

## 禁止事项

- 不要把某个 parser、builder、report 文件名或软件包声明为唯一合法路径
- 不要伪造文献、数据、计算结果、图表或 citation
- 不要保存 credentials 或受限许可文件
- 不要绕过 dry-run、approval gate 或 artifact lineage

## 需要人工确认的场景

- 真实 local/remote/HPC submit
- destructive file operation
- credentials、licensed/proprietary files 或高风险资源使用
- TODO: 列出该 skill 的其他人工确认场景
`;

fs.writeFileSync(path.join(skillDir, 'SKILL.md'), template);

console.log(`Skill created: ${skillName}`);
console.log(`  Directory: ${skillDir}`);
console.log(`  SKILL.md: ${path.join(skillDir, 'SKILL.md')}`);
