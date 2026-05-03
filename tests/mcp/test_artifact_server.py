#!/usr/bin/env python3
"""Tests for artifact_store MCP server."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from runtime.lib.artifact import register_artifact, list_artifacts, get_artifact


def test_register_artifact():
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_file = Path(tmpdir) / "test_output.json"
        artifact_file.write_text('{"result": "ok"}')

        art = register_artifact(
            "test_output", "analysis", "analysis", tmpdir,
            path=str(artifact_file)
        )
        assert art["type"] == "analysis"
        assert art["stage"] == "analysis"


def test_list_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(3):
            f = Path(tmpdir) / f"file_{i}.txt"
            f.write_text(f"content {i}")
            register_artifact(f"file_{i}", "test", "modeling", tmpdir, path=str(f))

        artifacts = list_artifacts(base_dir=tmpdir)
        assert len(artifacts) == 3


def test_list_artifacts_by_stage():
    with tempfile.TemporaryDirectory() as tmpdir:
        register_artifact("out1", "energy", "analysis", tmpdir)
        register_artifact("out2", "structure", "modeling", tmpdir)

        analysis_arts = list_artifacts(stage="analysis", base_dir=tmpdir)
        assert len(analysis_arts) == 1
        assert analysis_arts[0]["stage"] == "analysis"


def test_artifact_has_version():
    with tempfile.TemporaryDirectory() as tmpdir:
        register_artifact("data", "test", "compute", tmpdir)
        arts = list_artifacts(base_dir=tmpdir)
        assert "version" in arts[0]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        t()
        print("OK")
    print(f"\n  All {len(tests)} tests passed!")
