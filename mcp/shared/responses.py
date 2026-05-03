"""Standard MCP response helpers."""

from typing import Any


def success(data: Any = None, message: str = "OK") -> dict:
    """Create a success response."""
    return {"status": "success", "message": message, "data": data}


def error(message: str, code: str = "UNKNOWN") -> dict:
    """Create an error response."""
    return {"status": "error", "message": message, "code": code}


def validation_result(results: list) -> dict:
    """Create a validation result response."""
    overall = "pass"
    for r in results:
        if r.get("status") == "fail":
            overall = "fail"
            break
        elif r.get("status") == "warning":
            overall = "warning"
    return {"status": overall, "results": results}
