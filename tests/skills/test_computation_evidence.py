#!/usr/bin/env python3
"""Tests for record_computation_evidence without proposal artifacts.

Covers P0.4:
- record_computation_evidence succeeds when entry_point=computation and no
  proposal artifacts exist (the LBS 07/22 'Missing proposal artifacts' error)
- _allows_direct_contract checks workflow.json entry_point, not just metadata.json
- Projects entering at computation+ can record evidence without proposal stage
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # tests/skills/ -> simflow/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))
sys.path.insert(0, str(ROOT / "mcp" / "servers" / "simflow_state"))


def _init_workflow(*args, **kwargs):
    from runtime.simflow_core.state import init_workflow
    return init_workflow(*args, **kwargs)


def test_allows_direct_contract_with_workflow_entry_computation():
    """_allows_direct_contract returns True when workflow entry_point=computation."""
    from runtime.simflow_core.proposals import _allows_direct_contract

    metadata = {}  # empty metadata.json (typical for LBS project)
    workflow_state = {"entry_point": "computation", "current_stage": "computation"}

    assert _allows_direct_contract(metadata, "modeling", workflow_state=workflow_state) is True
    assert _allows_direct_contract(metadata, "computation", workflow_state=workflow_state) is True


def test_allows_direct_contract_returns_false_for_proposal_entry():
    """_allows_direct_contract returns False when entry_point=proposal."""
    from runtime.simflow_core.proposals import _allows_direct_contract

    metadata = {}
    workflow_state = {"entry_point": "proposal", "current_stage": "proposal"}

    assert _allows_direct_contract(metadata, "modeling", workflow_state=workflow_state) is False
    assert _allows_direct_contract(metadata, "computation", workflow_state=workflow_state) is False


def test_allows_direct_contract_uses_metadata_when_no_workflow_state():
    """_allows_direct_contract falls back to metadata when workflow_state is None."""
    from runtime.simflow_core.proposals import _allows_direct_contract

    metadata = {"entry_point": "computation", "current_stage": "computation"}
    assert _allows_direct_contract(metadata, "computation", workflow_state=None) is True

    metadata_empty = {}
    assert _allows_direct_contract(metadata_empty, "computation", workflow_state=None) is False


def test_load_proposal_contract_direct_entry_for_computation_project():
    """load_proposal_contract returns direct_entry contract for computation project.

    This is the core fix: a project initialized with entry_point=computation
    should be able to load_proposal_contract(allow_direct_entry=True) without
    having created proposal.md/parameter_table.csv/research_questions.json.
    """
    from runtime.simflow_core.proposals import load_proposal_contract

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow("mlp_nep_training", "computation", project_root=tmpdir)

        contract = load_proposal_contract(
            str(Path(tmpdir) / ".simflow"),
            allow_direct_entry=True,
        )

        assert contract["direct_entry"] is True
        assert contract["workflow_type"] == "mlp_nep_training"
        assert contract["proposal_artifacts"] == {}
        # source is inside proposal_contract, not at top level
        assert contract["proposal_contract"]["source"] == "direct_entry_metadata"


def test_load_proposal_contract_raises_for_proposal_entry_without_artifacts():
    """load_proposal_contract raises FileNotFoundError for proposal entry without artifacts.

    A project initialized with entry_point=proposal SHOULD have proposal artifacts.
    If they're missing, it's an error, not a direct-entry case.
    """
    from runtime.simflow_core.proposals import load_proposal_contract

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow("dft", "proposal", project_root=tmpdir)

        try:
            load_proposal_contract(
                str(Path(tmpdir) / ".simflow"),
                allow_direct_entry=True,
            )
            assert False, "should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "Missing proposal artifacts" in str(e)


def test_load_proposal_contract_works_with_artifacts():
    """load_proposal_contract loads artifacts when they exist."""
    from runtime.simflow_core.proposals import load_proposal_contract
    from runtime.simflow_core.state import init_workflow, write_state
    from runtime.simflow_core.artifacts import register_artifact

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow("dft", "proposal", project_root=tmpdir)

        # Register the 3 required proposal artifacts
        proposal_md = Path(tmpdir) / "proposal.md"
        proposal_md.write_text("# Test Proposal\n\nGoal: test", encoding="utf-8")
        register_artifact(
            "proposal.md", "proposal_document", "proposal",
            path="proposal.md", project_root=tmpdir,
        )

        param_csv = Path(tmpdir) / "parameter_table.csv"
        param_csv.write_text("parameter,value\nsoftware,vasp\n", encoding="utf-8")
        register_artifact(
            "parameter_table.csv", "parameter_table", "proposal",
            path="parameter_table.csv", project_root=tmpdir,
        )

        rq_json = Path(tmpdir) / "research_questions.json"
        rq_json.write_text('{"questions":[{"question":"What is the band gap?"}]}', encoding="utf-8")
        register_artifact(
            "research_questions.json", "research_questions", "proposal",
            path="research_questions.json", project_root=tmpdir,
        )

        contract = load_proposal_contract(
            str(Path(tmpdir) / ".simflow"),
            allow_direct_entry=True,
        )

        assert contract.get("direct_entry") is not True
        assert "proposal.md" in contract.get("proposal_artifacts", {})


def test_record_computation_evidence_succeeds_for_computation_project():
    """MCP record_computation_evidence succeeds for entry_point=computation.

    This is the integration test: the full MCP tool path should succeed
    without 'Missing proposal artifacts' error when entry_point=computation.
    """
    from runtime.simflow_core.state import init_workflow, write_state
    from runtime.simflow_core.artifacts import register_artifact

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow("mlp_nep_training", "computation", project_root=tmpdir)

        # Create a real evidence file
        evidence_file = Path(tmpdir) / "train.log"
        evidence_file.write_text("training started\n", encoding="utf-8")

        # Register it as an artifact first (record_computation_evidence expects paths)
        register_artifact(
            "train.log", "training_log", "computation",
            path="train.log", project_root=tmpdir,
        )

        # Now call record_computation_evidence via the MCP tool
        from tools.record_computation_evidence import execute

        result = execute({
            "project_root": tmpdir,
            "evidence_params": {
                "evidence": {
                    "input_files": [{"path": "train.log", "name": "train.log"}],
                },
                "software": "gpumd",
                "task": "nep_training",
                "dry_run": True,
            },
        })

        assert result["status"] == "success", f"expected success, got: {result}"


def test_record_computation_evidence_fails_for_proposal_entry_without_artifacts():
    """MCP record_computation_evidence fails for proposal entry without artifacts.

    A project with entry_point=proposal should not be able to record computation
    evidence without first creating proposal artifacts.
    """
    from runtime.simflow_core.state import init_workflow

    with tempfile.TemporaryDirectory() as tmpdir:
        _init_workflow("dft", "proposal", project_root=tmpdir)

        evidence_file = Path(tmpdir) / "train.log"
        evidence_file.write_text("training started\n", encoding="utf-8")

        from tools.record_computation_evidence import execute

        result = execute({
            "project_root": tmpdir,
            "evidence_params": {
                "evidence": {
                    "input_files": [{"path": "train.log", "name": "train.log"}],
                },
                "software": "vasp",
                "task": "relax",
                "dry_run": True,
            },
        })

        assert result["status"] == "error"
        assert "Missing proposal artifacts" in result.get("message", "") or \
               "proposal" in result.get("message", "").lower()


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
