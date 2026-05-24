#!/usr/bin/env python3
"""Compatibility wrapper for canonical stage executor helpers."""

from runtime.simflow_helpers.stages.executor import *  # noqa: F401,F403
from runtime.simflow_helpers.stages.executor import main


if __name__ == "__main__":
    main()
