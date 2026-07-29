import { existsSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

export const SERVER_NAMES = [
  "simflow_state",
  "artifact_store",
  "checkpoint_store",
  "literature",
  "structure",
  "hpc",
  "parsers",
]

async function resolvePluginRoot() {
  let cursor = path.dirname(fileURLToPath(import.meta.url))
  while (true) {
    const skill = path.join(cursor, "skills", "simflow", "SKILL.md")
    const startup = path.join(cursor, "scripts", "start_mcp_server.py")
    if (existsSync(skill) && existsSync(startup)) {
      return cursor
    }
    const parent = path.dirname(cursor)
    if (parent === cursor) {
      throw new Error("Unable to locate the SimFlow plugin root")
    }
    cursor = parent
  }
}

function sameCommand(existing, command) {
  return existing?.type === "local"
    && Array.isArray(existing.command)
    && existing.command.length === command.length
    && existing.command.every((value, index) => value === command[index])
}

export const SimFlowPlugin = async () => {
  const pluginRoot = await resolvePluginRoot()
  const skillsPath = path.join(pluginRoot, "skills")
  const startupScript = path.join(pluginRoot, "scripts", "start_mcp_server.py")
  const python = process.env.SIMFLOW_PYTHON || "python3"

  return {
    config: async (config) => {
      config.skills ??= {}
      config.skills.paths ??= []
      if (!config.skills.paths.includes(skillsPath)) {
        config.skills.paths.push(skillsPath)
      }

      config.mcp ??= {}
      for (const name of SERVER_NAMES) {
        const command = [python, startupScript, name]
        const existing = config.mcp[name]
        if (existing !== undefined) {
          if (!sameCommand(existing, command)) {
            console.warn(`[simflow] preserving existing OpenCode MCP configuration for ${name}`)
          }
          continue
        }
        config.mcp[name] = {
          type: "local",
          command,
          enabled: true,
          timeout: 10000,
        }
      }
    },
  }
}

export default {
  id: "simflow",
  server: SimFlowPlugin,
}
