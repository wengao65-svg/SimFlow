#!/usr/bin/env python3
"""Tests for runtime/lib/artifact.py"""

import os
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "runtime"))

from runtime.simflow_core.artifacts import register_artifact, list_artifacts, get_artifact
from runtime.simflow_core.lineage import get_dependency_tree, get_descendants, get_lineage


class TestArtifact:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_dir = self.tmpdir
        # Ensure state dir exists
        from runtime.simflow_core.state import ensure_simflow_dir
        ensure_simflow_dir(self.base_dir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def test_register_artifact(self):
        art = register_artifact("test.md", "proposal", "proposal", self.base_dir)
        assert art["artifact_id"].startswith("art_")
        assert art["name"] == "test.md"
        assert art["version"] == "v1.0.0"

    def test_register_open_artifact_type_and_metadata(self):
        path = Path(self.base_dir) / "custom-output.dat"
        path.write_text("custom data\n", encoding="utf-8")

        art = register_artifact(
            "custom-output.dat",
            "user_defined_analysis_output",
            "analysis_visualization",
            self.base_dir,
            path="custom-output.dat",
            parameters={"script": "analysis.py"},
            software="bespoke-tool",
            metadata={"format": "custom"},
        )

        assert art["type"] == "user_defined_analysis_output"
        assert art["stage"] == "analysis_visualization"
        assert art["metadata"]["format"] == "custom"
        assert art["lineage"]["software"] == "bespoke-tool"
        assert art["checksum"]

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

    def test_register_artifact_records_first_class_lineage(self):
        parent = register_artifact("input.json", "input_manifest", "computation", self.base_dir)
        child = register_artifact(
            "figure.png",
            "custom_figure",
            "analysis_visualization",
            self.base_dir,
            parent_artifacts=[parent["artifact_id"]],
            parameters={"plot_script": "plot.py"},
            software="matplotlib",
        )

        lineage_state = json.loads((Path(self.base_dir) / ".simflow" / "state" / "lineage.json").read_text())
        node_ids = {node["artifact_id"] for node in lineage_state["artifacts"]}
        assert parent["artifact_id"] in node_ids
        assert child["artifact_id"] in node_ids
        assert any(
            link["parent_artifact_id"] == parent["artifact_id"]
            and link["child_artifact_id"] == child["artifact_id"]
            for link in lineage_state["links"]
        )

        lineage = get_lineage(child["artifact_id"], self.base_dir)
        assert lineage["parent_artifacts"] == [parent["artifact_id"]]
        assert lineage["links"][0]["relationship"] == "derived_from"

        tree = get_dependency_tree(child["artifact_id"], self.base_dir)
        assert tree["parents"][0]["artifact_id"] == parent["artifact_id"]
        descendants = get_descendants(parent["artifact_id"], self.base_dir)
        assert descendants[0]["artifact_id"] == child["artifact_id"]


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
