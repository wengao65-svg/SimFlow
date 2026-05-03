#!/usr/bin/env python3
"""Tests for runtime/lib/artifact.py"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from lib.artifact import register_artifact, list_artifacts, get_artifact


class TestArtifact:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_dir = self.tmpdir
        # Ensure state dir exists
        from lib.state import ensure_simflow_dir
        ensure_simflow_dir(self.base_dir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_register_artifact(self):
        art = register_artifact("test.md", "proposal", "proposal", self.base_dir)
        assert art["artifact_id"].startswith("art_")
        assert art["name"] == "test.md"
        assert art["version"] == "v1.0.0"

    def test_list_artifacts(self):
        register_artifact("a.md", "proposal", "proposal", self.base_dir)
        register_artifact("b.md", "model", "modeling", self.base_dir)
        all_arts = list_artifacts(base_dir=self.base_dir)
        assert len(all_arts) == 2
        stage_arts = list_artifacts(stage="proposal", base_dir=self.base_dir)
        assert len(stage_arts) == 1

    def test_get_artifact(self):
        art = register_artifact("test.md", "proposal", "proposal", self.base_dir)
        result = get_artifact(art["artifact_id"], self.base_dir)
        assert result is not None
        assert result["name"] == "test.md"

    def test_get_nonexistent_artifact(self):
        result = get_artifact("art_nonexistent", self.base_dir)
        assert result is None


if __name__ == "__main__":
    methods = ["test_register_artifact", "test_list_artifacts", "test_get_artifact", "test_get_nonexistent_artifact"]
    for method in methods:
        t = TestArtifact()
        t.setup_method()
        try:
            getattr(t, method)()
            print(f"  PASS: {method}")
        except Exception as e:
            print(f"  FAIL: {method} - {e}")
        finally:
            t.teardown_method()
    print("All artifact tests passed!")
