"""Artifact Store MCP Server.

Tools: register, list, get
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "runtime"))

from tools.register import execute as register
from tools.list import execute as list_artifacts
from tools.get import execute as get_artifact

TOOLS = {
    "register": register,
    "list": list_artifacts,
    "get": get_artifact,
}


def handle_request(request: dict) -> dict:
    tool = request.get("tool")
    params = request.get("params", {})
    if tool not in TOOLS:
        return {"status": "error", "message": f"Unknown tool: {tool}"}
    try:
        return TOOLS[tool](params)
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    for line in sys.stdin:
        request = json.loads(line)
        response = handle_request(request)
        print(json.dumps(response))
        sys.stdout.flush()
