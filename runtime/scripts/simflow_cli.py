#!/usr/bin/env python3
"""Small SimFlow maintenance CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.migration import convert_workflow_file, inspect_legacy_project, migrate_project_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SimFlow workflow-layer maintenance tools")
    subcommands = parser.add_subparsers(dest="command", required=True)

    inspect = subcommands.add_parser("inspect-legacy", help="Inspect legacy .simflow state")
    inspect.add_argument("--project-root", required=True, help="User project root")

    migrate = subcommands.add_parser("migrate", help="Migrate legacy .simflow state")
    migrate.add_argument("--project-root", required=True, help="User project root")

    convert = subcommands.add_parser("convert-workflow", help="Convert legacy workflow JSON to recipe JSON")
    convert.add_argument("input", help="Legacy workflow JSON path")
    convert.add_argument("--output", help="Optional output recipe JSON path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inspect-legacy":
        result = inspect_legacy_project(args.project_root)
    elif args.command == "migrate":
        result = migrate_project_state(args.project_root)
    elif args.command == "convert-workflow":
        result = convert_workflow_file(args.input, args.output)
    else:  # pragma: no cover - argparse prevents this
        parser.error(f"Unknown command: {args.command}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
