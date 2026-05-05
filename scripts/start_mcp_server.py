#!/usr/bin/env python3
"""Start a SimFlow MCP server from an installed plugin directory.

Codex may launch plugin MCP commands without setting cwd to the plugin root.
This wrapper resolves the plugin root from its own path, prepares sys.path and
PYTHONPATH, then execs the requested server with plugin-root cwd.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


SERVER_PATHS = {
    "simflow_state": "mcp/servers/simflow_state/server.py",
    "artifact_store": "mcp/servers/artifact_store/server.py",
    "checkpoint_store": "mcp/servers/checkpoint_store/server.py",
    "literature": "mcp/servers/literature/server.py",
    "structure": "mcp/servers/structure/server.py",
    "hpc": "mcp/servers/hpc/server.py",
    "parsers": "mcp/servers/parsers/server.py",
}


def _fail(message: str, code: int = 2) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        names = ", ".join(sorted(SERVER_PATHS))
        _fail(f"Usage: start_mcp_server.py <server_name>. Valid servers: {names}")

    server_name = argv[1]
    relative_server_path = SERVER_PATHS.get(server_name)
    if relative_server_path is None:
        names = ", ".join(sorted(SERVER_PATHS))
        _fail(f"Unknown SimFlow MCP server: {server_name}. Valid servers: {names}")

    plugin_root = Path(__file__).resolve().parents[1]
    server_path = plugin_root / relative_server_path
    if not server_path.is_file():
        _fail(f"SimFlow MCP server file not found: {server_path}", code=1)

    env = os.environ.copy()
    python_path_entries = [str(plugin_root), str(plugin_root / "runtime")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        python_path_entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(python_path_entries)

    os.chdir(plugin_root)
    os.execvpe(sys.executable, [sys.executable, str(server_path)], env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
