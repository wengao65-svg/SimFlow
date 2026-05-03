"""SimFlow State MCP Server.

Provides tools for workflow state management.
Tools: read_state, write_state, init_workflow, update_stage
"""

import json
import sys
from pathlib import Path

# Add runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "runtime"))

from tools.read_state import execute as read_state
from tools.write_state import execute as write_state
from tools.init_workflow import execute as init_workflow
from tools.update_stage import execute as update_stage

TOOLS = {
    "read_state": read_state,
    "write_state": write_state,
    "init_workflow": init_workflow,
    "update_stage": update_stage,
}


def handle_request(request: dict) -> dict:
    """Handle an MCP request."""
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
