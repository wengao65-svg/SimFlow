"""Parsers MCP Server.

Provides computational chemistry output parsing tools.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "runtime"))

from lib.parsers.vasp_parser import VASPParser
from lib.parsers.qe_parser import QEParser
from lib.parsers.lammps_parser import LAMMPSParser
from lib.parsers.gaussian_parser import GaussianParser

PARSERS = {
    "vasp": VASPParser,
    "qe": QEParser,
    "lammps": LAMMPSParser,
    "gaussian": GaussianParser,
}


def handle_parse(params: dict) -> dict:
    software = params.get("software", "").lower()
    file_path = params.get("file_path", "")
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
    software = params.get("software", "").lower()
    file_path = params.get("file_path", "")
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
