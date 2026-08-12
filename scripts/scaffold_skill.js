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

- TODO: 列出可接受的输入、用户提供文件和必要上下文

## 输出指导

- TODO: 描述该 Skill 应提供的建议、检查或可选 helper
- TODO: 说明结论应如何受现有证据约束

## Runtime 边界

- Skill 本身不要求状态写入、阶段转换、artifact 注册或 checkpoint
- 仅当真实事件需要检查、持久记录、审批或恢复时，由 host 调用 runtime
- runtime 操作必须接收显式 project_root，不得从 plugin root、MCP cwd 或 \`.omx/\` 推断

## 禁止事项

- 不要把某个 parser、builder、report 文件名或软件包声明为唯一合法路径
- 不要伪造文献、数据、计算结果、图表或 citation
- 不要保存 credentials 或受限许可文件
- 不要绕过 immutable run plan、绑定审批或 public HPC runtime

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
