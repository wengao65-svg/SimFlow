#!/usr/bin/env python3
"""Compatibility wrapper for canonical project intake helpers."""

from runtime.simflow_helpers.project.intake import *  # noqa: F401,F403
from runtime.simflow_helpers.project.intake import main


if __name__ == "__main__":
    main()
