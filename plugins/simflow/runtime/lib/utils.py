"""General-purpose file, path, time, and ID utilities."""

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def generate_id(prefix: str = "") -> str:
    """Generate a short unique ID with optional prefix."""
    short = uuid.uuid4().hex[:8]
    return f"{prefix}{short}" if prefix else short


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def safe_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name).strip("_")


def ensure_dir(path: str) -> Path:
    """Ensure a directory exists and return it as Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: str) -> Any:
    """Read a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(data: Any, path: str, indent: int = 2) -> Path:
    """Write data to a JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    return p


def compute_checksum(file_path: str, algorithm: str = "sha256") -> str:
    """Compute file checksum."""
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def file_size(file_path: str) -> int:
    """Get file size in bytes."""
    return os.path.getsize(file_path)


def relative_path(target: str, base: str = ".") -> str:
    """Get relative path from base to target."""
    return os.path.relpath(target, base)


def find_files(directory: str, pattern: str = "*", recursive: bool = False) -> list:
    """Find files matching a glob pattern."""
    p = Path(directory)
    if not p.exists():
        return []
    glob_func = p.rglob if recursive else p.glob
    return sorted(str(f) for f in glob_func(pattern) if f.is_file())


def merge_dicts(base: dict, override: dict) -> dict:
    """Deep merge two dicts, override takes precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result
