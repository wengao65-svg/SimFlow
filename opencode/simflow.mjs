import { existsSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

async function resolvePluginRoot() {
  let cursor = path.dirname(fileURLToPath(import.meta.url))
  while (true) {
    const skill = path.join(cursor, "skills", "simflow-vasp", "SKILL.md")
    if (existsSync(skill)) {
      return cursor
    }
    const parent = path.dirname(cursor)
    if (parent === cursor) {
      throw new Error("Unable to locate the SimFlow plugin root")
    }
    cursor = parent
  }
}

export const SimFlowPlugin = async () => {
  const pluginRoot = await resolvePluginRoot()
  const skillsPath = path.join(pluginRoot, "skills")
  return {
    config: async (config) => {
      config.skills ??= {}
      config.skills.paths ??= []
      if (!config.skills.paths.includes(skillsPath)) {
        config.skills.paths.push(skillsPath)
      }

      // Installing SimFlow only adds Skills. User configured MCP servers are
      // left untouched and are never replaced by a SimFlow server.
    },
  }
}

export default {
  id: "simflow",
  server: SimFlowPlugin,
}
