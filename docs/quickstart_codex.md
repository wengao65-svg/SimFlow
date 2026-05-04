# SimFlow v0.7.0 — Codex 快速上手指南

本指南说明如何按官方 Codex 插件流程发现、安装并验证 SimFlow。

## 前置条件

- Python 3.10+
- OpenAI Codex CLI 已安装（`npm install -g @openai/codex`）

## 第一步：获取 SimFlow

```bash
# 方式一：git clone
git clone https://github.com/<your-org>/simflow.git
cd simflow

# 方式二：下载 release 解压后进入目录
cd simflow-0.7.0
```

## 第二步：理解仓库里的 Codex 入口

SimFlow 现在通过官方 Codex 插件结构暴露能力：

| 路径 | 作用 |
|------|------|
| `.codex-plugin/plugin.json` | Codex 插件 manifest，声明插件身份、skills 和 MCP 入口 |
| `.mcp.json` | 插件根目录下的 MCP server 注册表 |
| `.agents/plugins/marketplace.json` | 本地 marketplace 入口，让 `/plugins` 可发现 SimFlow |
| `.agents/skills` | repo 级 skills 兼容层，指向仓库中的 `skills/` |
| `AGENTS.md` | 给 Codex 的项目上下文与行为约束，不负责插件注册 |

说明：
- `hooks/internal_workflow_hooks.json` 是 **SimFlow 内部 workflow hooks**，不是 Codex lifecycle hooks。
- `mcp/.mcp.json` 保留为仓库内部 MCP 定义来源，Codex 读取的是根目录 `/.mcp.json`。

## 第三步：在 Codex 中发现并安装插件

在仓库根目录启动 Codex：

```bash
codex
```

然后在 Codex 会话中执行：

```text
/plugins
```

预期结果：
- 可以看到本地 marketplace（`SimFlow Local Plugins`）
- 可以看到 `simflow` 插件
- 安装后插件会显示为已启用

如果 `/plugins` 中没有看到 SimFlow：
- 确认当前工作目录是仓库根目录 `simflow/`
- 确认 `.agents/plugins/marketplace.json` 存在
- 确认 `.codex-plugin/plugin.json` 和 `/.mcp.json` 存在

## 第四步：验证 MCP 已被 Codex 识别

插件启用后，在 Codex 会话中执行：

```text
/mcp
```

预期结果：
- 能看到以下 7 个 SimFlow MCP servers：
  - `simflow_state`
  - `artifact_store`
  - `checkpoint_store`
  - `literature`
  - `structure`
  - `hpc`
  - `parsers`

如果某个 MCP server 没有显示：
- 先检查 `/.mcp.json` 中对应配置
- 再检查命令路径（如 `mcp/servers/.../server.py`）在当前仓库内是否存在

## 第五步：验证 skills 已被 Codex 识别

优先尝试：

```text
/skills
```

如果当前 Codex build 支持列出 repo/plugin skills，预期应能看到 SimFlow skills。

如果 `/skills` 没有列出内容或当前版本未提供稳定输出，也可以按下面两种方式验证：

1. **结构验证**
   - `.agents/skills` 已指向仓库的 `skills/`
   - 每个 `skills/*/SKILL.md` 都带有合法 frontmatter（`name`、`description`）

2. **行为验证**
   在 Codex 对话中输入：

   ```text
   用 SimFlow 构建一个 Si 的金刚石晶体结构
   ```

   或者：

   ```text
   用 SimFlow 为 H2O 规划一个 CP2K AIMD 工作流
   ```

   如果 Codex 能命中 SimFlow 的入口/建模/CP2K skills，并继续调用对应 MCP 或 workflow 逻辑，说明 skills 已经可用。

## 第六步：运行仓库自检

在仓库根目录执行：

```bash
npm run validate:plugin
npm run validate:skills
```

这两个校验会检查：
- 插件 manifest 是否使用 Codex 官方字段
- 根目录 `/.mcp.json` 和本地 marketplace 入口是否存在
- `SKILL.md` 是否具备 `name` / `description` frontmatter
- 现有 SimFlow skill 正文结构是否完整

## 基本使用

SimFlow 通过自然语言驱动。在 Codex 对话中直接描述需求即可：

**结构建模**
```text
帮我构建一个 FCC 铜晶体，晶格常数 3.61 Å，然后建 2x2x2 超胞
```

**DFT 工作流**
```text
用 VASP 对 Si 做 DFT 计算：先结构弛豫，再自洽计算，最后能带分析
```

**AIMD 工作流**
```text
对 H2O 做 AIMD 分子动力学模拟，使用 CP2K，NVT 系综，300K，1000 步
```

**文献搜索**
```text
搜索 arXiv 上关于钙钛矿太阳能电池的最新论文
```

**结构数据库查询**
```text
从 Crystallography Open Database 查询 SiO2 的晶体结构
```

所有计算操作默认为 **dry-run 模式**，不会真正提交 HPC 作业。需要实际提交时，Codex 会要求你确认。

## 环境变量配置（可选）

如需连接 HPC 集群或使用外部 API，在启动 Codex 前设置：

```bash
# HPC 连接
export SIMFLOW_HPC_HOST="hpc"
export SIMFLOW_HPC_BASE="/home/$USER/jobs"
export SIMFLOW_PARTITION="cpu"
export SIMFLOW_NTASKS="32"

# CP2K（如使用）
export SIMFLOW_CP2K_ENV="source /opt/cp2k/v2025.1/scripts/env.sh"
export SIMFLOW_CP2K_EXE="cp2k.psmp"

# VASP（如使用）
export SIMFLOW_VASP_ENV="source /opt/vasp/6.4.2/env.sh"

# 外部 API（可选，缺失时自动回退到模拟模式）
export MP_API_KEY="your-materials-project-key"
export S2_API_KEY="your-semantic-scholar-key"
```

## 常见问题

**Q: `/plugins` 里没有看到 SimFlow**
- 确认你是在仓库根目录运行 `codex`
- 确认 `.agents/plugins/marketplace.json` 存在且路径指向当前仓库
- 确认 `.codex-plugin/plugin.json` 使用的是官方字段

**Q: `/mcp` 中没有看到 SimFlow 工具**
- 确认插件已通过 `/plugins` 安装并启用
- 检查根目录 `/.mcp.json`
- 检查 Python 3.10+ 是否可用：`python --version`

**Q: `/skills` 没有稳定列出 SimFlow skills**
- 这取决于当前 Codex build 的 CLI 暴露方式
- 先用 `npm run validate:skills` 做结构校验
- 再通过自然语言请求验证 skill 是否被实际命中

**Q: 找不到 pymatgen / MDAnalysis 模块**
- 结构建模和轨迹分析需要可选依赖：
  ```bash
  pip install "simflow[all]"
  ```

**Q: SSH 连接 HPC 失败**
- 测试连通性：`ssh -o ConnectTimeout=10 hpc hostname`
- 检查 `~/.ssh/config` 中的 Host 配置

**Q: 如何退出 dry-run 模式？**
- 在 Codex 对话中明确要求：`提交这个作业到 HPC`
- Codex 会通过 approval gate 请求你确认
