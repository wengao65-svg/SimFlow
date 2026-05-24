#!/usr/bin/env python3
"""Compatibility wrapper for canonical stage pipeline helpers."""

from runtime.simflow_helpers.stages.pipeline import *  # noqa: F401,F403
from runtime.simflow_helpers.stages.pipeline import main


if __name__ == "__main__":
    main()
