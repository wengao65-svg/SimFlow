#!/usr/bin/env python3
"""CLI entry point for SimFlow scientific reference extraction."""

from __future__ import annotations

from _reference_extractor import main as run_cli


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
