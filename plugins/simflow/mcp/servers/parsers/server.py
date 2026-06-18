"""Parsers MCP Server.

Provides computational chemistry output parsing tools.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))

from runtime.simflow_helpers.engines.parsers.cp2k_parser import CP2KParser
from runtime.simflow_helpers.engines.parsers.vasp_parser import VASPParser
from runtime.simflow_helpers.engines.parsers.lammps_parser import LAMMPSParser
from runtime.simflow_core.toolchains import normalize_tool_name
from mcp.shared.stdio_server import run_mcp_server

PARSERS = {
    "cp2k": CP2KParser,
    "vasp": VASPParser,
    "lammps": LAMMPSParser,
}

UNSUPPORTED_PLACEHOLDERS = {"qe", "quantum_espresso", "gaussian"}


def _normalized_software(value: object) -> str:
    return normalize_tool_name(value)


def _unsupported_placeholder(software: str) -> dict:
    return {
        "status": "unsupported_placeholder",
        "software": software,
        "message": (
            "QE and Gaussian parser/validation helpers are not supported in this "
            "SimFlow product build. Record user-provided files through generic "
            "artifact or evidence intake with explicit unsupported provenance."
        ),
    }


def handle_parse(params: dict) -> dict:
    software = _normalized_software(params.get("software", ""))
    file_path = params.get("file_path", "")
    if software in UNSUPPORTED_PLACEHOLDERS:
        return _unsupported_placeholder(software)
    if software not in PARSERS:
        return {"status": "error", "message": f"Unsupported: {software}"}
    if not file_path:
        return {"status": "error", "message": "file_path is required"}
    try:
        parser = PARSERS[software]()
        result = parser.parse(file_path)
        from dataclasses import asdict
        return {"status": "success", "data": asdict(result)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def handle_check_convergence(params: dict) -> dict:
    software = _normalized_software(params.get("software", ""))
    file_path = params.get("file_path", "")
    if software in UNSUPPORTED_PLACEHOLDERS:
        return _unsupported_placeholder(software)
    if software not in PARSERS:
        return {"status": "error", "message": f"Unsupported: {software}"}
    try:
        parser = PARSERS[software]()
        result = parser.check_convergence(file_path)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


TOOLS = {
    "parse": handle_parse,
    "check_convergence": handle_check_convergence,
}

TOOL_DESCRIPTIONS = {
    "parse": "Parse computational chemistry output files into structured data.",
    "check_convergence": "Check calculation convergence from supported output files.",
}

TOOL_SCHEMAS = {
    "parse": {
        "type": "object",
        "required": ["software", "file_path"],
        "properties": {
            "software": {"type": "string"},
            "file_path": {"type": "string"},
        },
        "additionalProperties": False,
    },
    "check_convergence": {
        "type": "object",
        "required": ["software", "file_path"],
        "properties": {
            "software": {"type": "string"},
            "file_path": {"type": "string"},
        },
        "additionalProperties": False,
    },
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
    run_mcp_server("parsers", TOOLS, TOOL_DESCRIPTIONS, TOOL_SCHEMAS)
