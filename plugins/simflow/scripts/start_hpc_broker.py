#!/usr/bin/env python3
"""Start the isolated SimFlow HPC credential broker from a plugin install."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    plugin_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(plugin_root))
    sys.path.insert(0, str(plugin_root / "runtime"))
    sys.path.insert(0, str(plugin_root / "mcp" / "servers" / "hpc"))

    from mcp.servers.hpc.broker_server import main as broker_main

    return broker_main()


if __name__ == "__main__":
    raise SystemExit(main())
