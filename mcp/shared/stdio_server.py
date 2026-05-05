"""Minimal stdio MCP transport for SimFlow servers.

This adapter speaks JSON-RPC over stdin/stdout so Codex can initialize the
servers with /mcp while existing SimFlow tool handlers remain plain functions.
"""

import json
import sys
from typing import Callable, Dict, Optional


DEFAULT_PROTOCOL_VERSION = "2024-11-05"


def _json_text(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _success_response(request_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error_response(request_id, code: int, message: str, data: Optional[dict] = None) -> dict:
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }
    if data:
        response["error"]["data"] = data
    return response


def _write(message: dict) -> None:
    print(_json_text(message))
    sys.stdout.flush()


def _tool_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": True,
        "properties": {},
    }


def _list_tools(
    tools: Dict[str, Callable],
    descriptions: Optional[Dict[str, str]] = None,
) -> list:
    descriptions = descriptions or {}
    return [
        {
            "name": name,
            "description": descriptions.get(name, f"SimFlow tool: {name}"),
            "inputSchema": _tool_schema(),
        }
        for name in sorted(tools)
    ]


def _call_tool(tools: Dict[str, Callable], params: dict) -> dict:
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not name:
        raise ValueError("tools/call requires params.name")
    if name not in tools:
        raise KeyError(f"Unknown tool: {name}")
    result = tools[name](arguments if isinstance(arguments, dict) else {})
    is_error = isinstance(result, dict) and result.get("status") == "error"
    return {
        "content": [{"type": "text", "text": _json_text(result)}],
        "isError": bool(is_error),
    }


def run_mcp_server(
    server_name: str,
    tools: Dict[str, Callable],
    descriptions: Optional[Dict[str, str]] = None,
    version: str = "0.8.0",
) -> None:
    """Run a JSON-RPC stdio MCP server.

    Supported methods are the minimum set Codex needs for server startup and
    tool discovery: initialize, tools/list, tools/call, ping, plus empty
    resources/list and prompts/list responses.
    """

    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue

        try:
            request = json.loads(raw)
        except json.JSONDecodeError as exc:
            _write(_error_response(None, -32700, f"Parse error: {exc}"))
            continue

        # Backward-compatible local module mode used by older SimFlow tests.
        if isinstance(request, dict) and "tool" in request and "jsonrpc" not in request:
            tool_name = request.get("tool")
            params = request.get("params", {})
            try:
                if tool_name not in tools:
                    legacy_result = {"status": "error", "message": f"Unknown tool: {tool_name}"}
                else:
                    legacy_result = tools[tool_name](params if isinstance(params, dict) else {})
            except Exception as exc:
                legacy_result = {"status": "error", "message": str(exc)}
            _write(legacy_result)
            continue

        request_id = request.get("id") if isinstance(request, dict) else None
        method = request.get("method") if isinstance(request, dict) else None
        params = request.get("params", {}) if isinstance(request, dict) else {}

        # Notifications have no id and must not receive a response.
        if request_id is None and isinstance(method, str) and method.startswith("notifications/"):
            continue

        try:
            if method == "initialize":
                client_version = None
                if isinstance(params, dict):
                    client_version = params.get("protocolVersion")
                _write(
                    _success_response(
                        request_id,
                        {
                            "protocolVersion": client_version or DEFAULT_PROTOCOL_VERSION,
                            "capabilities": {"tools": {"listChanged": False}},
                            "serverInfo": {"name": server_name, "version": version},
                        },
                    )
                )
            elif method == "ping":
                _write(_success_response(request_id, {}))
            elif method == "shutdown":
                _write(_success_response(request_id, {}))
                break
            elif method == "tools/list":
                _write(_success_response(request_id, {"tools": _list_tools(tools, descriptions)}))
            elif method == "tools/call":
                _write(_success_response(request_id, _call_tool(tools, params if isinstance(params, dict) else {})))
            elif method == "resources/list":
                _write(_success_response(request_id, {"resources": []}))
            elif method == "prompts/list":
                _write(_success_response(request_id, {"prompts": []}))
            else:
                _write(_error_response(request_id, -32601, f"Method not found: {method}"))
        except KeyError as exc:
            _write(_error_response(request_id, -32602, str(exc)))
        except Exception as exc:
            _write(_error_response(request_id, -32000, str(exc)))
