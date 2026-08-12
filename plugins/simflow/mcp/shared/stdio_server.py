"""Minimal stdio MCP transport for SimFlow servers.

This adapter speaks JSON-RPC over stdin/stdout so Codex can initialize the
servers with /mcp while existing SimFlow tool handlers remain plain functions.
"""

import json
import sys
from typing import Callable, Dict, Optional

from runtime.simflow_core.host_adaptation import build_initialize_instructions


DEFAULT_PROTOCOL_VERSION = "2024-11-05"
SERVER_NOT_INITIALIZED = -32002


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


def _tool_schema(name: str, schemas: Optional[Dict[str, dict]] = None) -> dict:
    if schemas and name in schemas:
        return schemas[name]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {},
    }


def _list_tools(
    tools: Dict[str, Callable],
    descriptions: Optional[Dict[str, str]] = None,
    schemas: Optional[Dict[str, dict]] = None,
) -> list:
    descriptions = descriptions or {}
    return [
        {
            "name": name,
            "description": descriptions.get(name, f"SimFlow tool: {name}"),
            "inputSchema": _tool_schema(name, schemas),
        }
        for name in sorted(tools)
    ]


def _call_tool(
    tools: Dict[str, Callable],
    params: dict,
    request_handler: Optional[Callable[[dict], dict]] = None,
) -> dict:
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not name:
        raise ValueError("tools/call requires params.name")
    if name not in tools:
        raise KeyError(f"Unknown tool: {name}")
    tool_arguments = arguments if isinstance(arguments, dict) else {}
    result = (
        request_handler({"tool": name, "params": tool_arguments})
        if request_handler is not None
        else tools[name](tool_arguments)
    )
    is_error = isinstance(result, dict) and result.get("status") == "error"
    return {
        "content": [{"type": "text", "text": _json_text(result)}],
        "isError": bool(is_error),
    }


def run_mcp_server(
    server_name: str,
    tools: Dict[str, Callable],
    descriptions: Optional[Dict[str, str]] = None,
    schemas: Optional[Dict[str, dict]] = None,
    version: str = "0.8.1",
    request_handler: Optional[Callable[[dict], dict]] = None,
) -> None:
    """Run a JSON-RPC stdio MCP server.

    Supported methods are the minimum set Codex needs for server startup and
    tool discovery: initialize, tools/list, tools/call, ping, plus empty
    resources/list and prompts/list responses.
    """

    initialize_received = False
    initialized = False

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
                    tool_params = params if isinstance(params, dict) else {}
                    legacy_result = (
                        request_handler({"tool": tool_name, "params": tool_params})
                        if request_handler is not None
                        else tools[tool_name](tool_params)
                    )
            except Exception as exc:
                legacy_result = {"status": "error", "message": str(exc)}
            _write(legacy_result)
            continue

        has_request_id = isinstance(request, dict) and "id" in request
        request_id = request.get("id") if has_request_id else None
        method = request.get("method") if isinstance(request, dict) else None
        params = request.get("params", {}) if isinstance(request, dict) else {}

        # Legacy MCP notifications have no id and must not receive a response.
        if not has_request_id and method == "notifications/initialized":
            if initialize_received:
                initialized = True
            continue
        if not has_request_id and isinstance(method, str):
            continue

        try:
            if method == "initialize":
                client_info = None
                if isinstance(params, dict):
                    client_info = params.get("clientInfo")
                initialize_received = True
                initialized = False
                result = {
                    "protocolVersion": DEFAULT_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": server_name, "version": version},
                }
                instructions = build_initialize_instructions(server_name, client_info)
                if instructions:
                    result["instructions"] = instructions
                _write(
                    _success_response(
                        request_id,
                        result,
                    )
                )
            elif method == "ping":
                _write(_success_response(request_id, {}))
            elif method == "shutdown":
                _write(_success_response(request_id, {}))
                break
            elif not initialized:
                _write(_error_response(
                    request_id,
                    SERVER_NOT_INITIALIZED,
                    "Server not initialized: send notifications/initialized after initialize",
                ))
            elif method == "tools/list":
                _write(_success_response(request_id, {"tools": _list_tools(tools, descriptions, schemas)}))
            elif method == "tools/call":
                _write(_success_response(
                    request_id,
                    _call_tool(
                        tools,
                        params if isinstance(params, dict) else {},
                        request_handler=request_handler,
                    ),
                ))
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
