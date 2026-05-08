"""MCP request/response serialization and transport helpers."""

import json
import sys
from typing import Any, Callable, Dict, Optional

from .errors import SimFlowError


def read_request(line: str) -> dict:
    """Parse a JSON request line.

    Args:
        line: Raw JSON string from stdin

    Returns:
        Parsed request dict

    Raises:
        SimFlowError: If JSON is invalid
    """
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        raise SimFlowError(f"Invalid JSON request: {e}", code="PARSE_ERROR")


def write_response(response: dict) -> None:
    """Write a JSON response to stdout and flush."""
    print(json.dumps(response, ensure_ascii=False))
    sys.stdout.flush()


def success_response(data: Any = None, message: str = "OK") -> dict:
    """Create a success response."""
    resp = {"status": "success", "message": message}
    if data is not None:
        resp["data"] = data
    return resp


def error_response(message: str, code: str = "UNKNOWN") -> dict:
    """Create an error response."""
    return {"status": "error", "message": message, "code": code}


def dispatch_request(
    request: dict,
    tools: Dict[str, Callable],
) -> dict:
    """Dispatch a request to the appropriate tool handler.

    Args:
        request: Parsed request dict with 'tool' and 'params' keys
        tools: Map of tool names to handler functions

    Returns:
        Response dict
    """
    tool = request.get("tool")
    params = request.get("params", {})

    if not tool:
        return error_response("Missing 'tool' field in request", "VALIDATION_ERROR")

    if tool not in tools:
        return error_response(f"Unknown tool: {tool}", "UNKNOWN_TOOL")

    try:
        result = tools[tool](params)
        if isinstance(result, dict) and "status" in result:
            return result
        return success_response(result)
    except SimFlowError as e:
        return error_response(str(e), e.code)
    except Exception as e:
        return error_response(str(e))


def run_server(tools: Dict[str, Callable]) -> None:
    """Run an MCP server reading from stdin.

    Args:
        tools: Map of tool names to handler functions
    """
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = read_request(line)
            response = dispatch_request(request, tools)
        except SimFlowError as e:
            response = error_response(str(e), e.code)
        write_response(response)
