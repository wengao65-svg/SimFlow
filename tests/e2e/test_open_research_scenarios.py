#!/usr/bin/env python3
"""Acceptance scenarios for the open SimFlow workflow layer."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.simflow_core.artifacts import list_artifacts, register_artifact
from runtime.simflow_core.checkpoints import create_checkpoint
from runtime.simflow_core.helpers import record_helper_run
from runtime.simflow_core.lineage import get_lineage
from runtime.simflow_core.state import init_workflow, read_state
from runtime.simflow_helpers.engines.vasp_workflows import build_vasp_task_plan, classify_vasp_request
from runtime.simflow_helpers.project.intake import init_research
from runtime.simflow_helpers.legacy_workflow.generate_literature_matrix import generate_literature_matrix


def test_user_pdf_literature_review_tracks_sources_without_fixed_provider(tmp_path):
    state = init_workflow("custom", "literature_review", project_root=str(tmp_path))
    pdf = tmp_path / "literature" / "paper.pdf"
    search_log = tmp_path / "literature" / "search_log.json"
    notes = tmp_path / "literature" / "paper_notes" / "paper.md"
    summary = tmp_path / "literature" / "review_summary.md"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    notes.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4 user provided placeholder\n")
    search_log.write_text(
        json.dumps({"source": "user_uploaded_pdf", "query": None, "full_text_access": "provided_by_user"}),
        encoding="utf-8",
    )
    notes.write_text("Direct quotes and interpretation are separated.\n", encoding="utf-8")
    summary.write_text("Evidence-traceable review summary.\n", encoding="utf-8")

    pdf_artifact = register_artifact(
        "paper.pdf",
        "user_uploaded_pdf",
        "literature_review",
        project_root=str(tmp_path),
        path="literature/paper.pdf",
        metadata={"source": "user_upload", "full_text_access": "provided_by_user"},
    )
    log_artifact = register_artifact(
        "search_log.json",
        "literature_search_log",
        "literature_review",
        project_root=str(tmp_path),
        path="literature/search_log.json",
        parent_artifacts=[pdf_artifact["artifact_id"]],
    )
    register_artifact(
        "review_summary.md",
        "literature_review_summary",
        "literature_review",
        project_root=str(tmp_path),
        path="literature/review_summary.md",
        parent_artifacts=[pdf_artifact["artifact_id"], log_artifact["artifact_id"]],
    )
    checkpoint = create_checkpoint(
        state["workflow_id"],
        "literature_review",
        "PDF literature review evidence recorded",
        project_root=str(tmp_path),
    )

    artifacts = read_state(project_root=str(tmp_path), state_file="artifacts.json")
    assert {artifact["type"] for artifact in artifacts} >= {
        "user_uploaded_pdf",
        "literature_search_log",
        "literature_review_summary",
    }
    assert artifacts[0]["metadata"]["source"] == "user_upload"
    assert checkpoint["stage_id"] == "literature_review"


def test_generate_literature_matrix_emits_canonical_search_log_and_citation_map(tmp_path):
    """The literature matrix script must emit the real schema, not a manual stub."""
    pdf_path = tmp_path / "papers" / "surface.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_text("pdf placeholder", encoding="utf-8")

    init_research(
        input_text="\n".join([
            "goal: study Si surface reconstruction",
            "material: Si(001)",
            "pdfs: papers/surface.pdf",
            "dois: 10.1000/surface",
            "note: Focus on dimer buckling evidence",
        ]),
        output_dir=str(tmp_path),
    )

    result = generate_literature_matrix(str(tmp_path / ".simflow"))
    assert result["status"] == "success"

    literature_dir = tmp_path / ".simflow" / "artifacts" / "literature"
    search_log = json.loads((literature_dir / "search_log.json").read_text(encoding="utf-8"))
    citation_map = json.loads((literature_dir / "citation_map.json").read_text(encoding="utf-8"))

    assert search_log["source_policy"] == "user_provided_or_agent_selected_sources"
    assert search_log["provider_constraints"] == "none_fixed_by_simflow"
    access_statuses = {source["access_status"] for source in search_log["sources"]}
    assert "full_text_provided_by_user" in access_statuses
    assert "metadata_only_full_text_not_accessed" in access_statuses
    assert "manual_note_no_external_full_text" in access_statuses

    assert citation_map["entries"]
    for entry in citation_map["entries"]:
        assert entry["access_status"]
        assert entry["verification_status"]
    doi_entry = next(entry for entry in citation_map["entries"] if entry.get("locator") == "10.1000/surface")
    assert doi_entry["access_status"] == "metadata_only_full_text_not_accessed"

    artifacts = list_artifacts(project_root=str(tmp_path), stage="literature_review")
    artifact_types = {artifact["type"] for artifact in artifacts}
    assert {"search_log", "citation_map", "paper_notes"}.issubset(artifact_types)


def test_user_provided_poscar_modeling_preserves_original_and_lineage(tmp_path):
    init_workflow("custom", "modeling", project_root=str(tmp_path))
    poscar = tmp_path / "POSCAR"
    converted = tmp_path / "models" / "structure.cif"
    poscar.write_text("Si\n1.0\n1 0 0\n0 1 0\n0 0 1\nSi\n1\nDirect\n0 0 0\n", encoding="utf-8")
    converted.parent.mkdir(parents=True, exist_ok=True)
    converted.write_text("data_Si\n", encoding="utf-8")

    original = register_artifact(
        "POSCAR",
        "user_provided_structure",
        "modeling",
        project_root=str(tmp_path),
        path="POSCAR",
        metadata={"source": "user_provided", "preserve_original": True},
    )
    model = register_artifact(
        "structure.cif",
        "converted_structure",
        "modeling",
        project_root=str(tmp_path),
        path="models/structure.cif",
        parent_artifacts=[original["artifact_id"]],
        software="pymatgen_or_ase_optional",
        metadata={"conversion": "optional_helper_or_agent_script"},
    )

    artifacts = read_state(project_root=str(tmp_path), state_file="artifacts.json")
    assert artifacts[0]["name"] == "POSCAR"
    assert artifacts[0]["checksum"]
    assert poscar.read_text(encoding="utf-8").startswith("Si\n1.0")
    lineage = get_lineage(model["artifact_id"], project_root=str(tmp_path))
    assert original["artifact_id"] in lineage["parent_artifacts"]


def test_vasp_phonon_and_neb_plans_are_not_forced_to_static(tmp_path):
    (tmp_path / "POSCAR").write_text("POSCAR placeholder\n", encoding="utf-8")
    phonon = classify_vasp_request("Plan a VASP phonon calculation", ["POSCAR"])
    neb = classify_vasp_request("Design a VASP NEB calculation", ["POSCAR", "INCAR", "KPOINTS", "POTCAR"])
    phonon_plan = build_vasp_task_plan("Plan a VASP phonon calculation", str(tmp_path))
    neb_plan = build_vasp_task_plan("Design a VASP NEB calculation", str(tmp_path))

    assert phonon["task"] == "unknown"
    assert phonon["status"] == "needs_clarification"
    assert phonon["candidates"]
    assert phonon_plan["task"] == "unknown"
    assert phonon_plan["compute_plan"]["real_submit_allowed"] is False

    assert neb["task"] == "neb_basic"
    assert neb_plan["task"] == "neb_basic"
    assert neb_plan["stage"] == "computation"
    assert neb_plan["task"] != "static"


def test_self_written_python_analysis_records_script_inputs_outputs_and_lineage(tmp_path):
    init_workflow("custom", "analysis_visualization", project_root=str(tmp_path))
    (tmp_path / "analysis").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "figures").mkdir()
    (tmp_path / "analysis" / "parse_outputs.py").write_text("print('parse')\n", encoding="utf-8")
    (tmp_path / "data" / "OUTCAR").write_text("energy -1.0\n", encoding="utf-8")
    (tmp_path / "analysis" / "summary.csv").write_text("step,energy\n0,-1.0\n", encoding="utf-8")
    (tmp_path / "figures" / "energy.png").write_text("png placeholder\n", encoding="utf-8")

    result = record_helper_run(
        project_root=str(tmp_path),
        stage="analysis_visualization",
        run_name="custom python output analysis",
        helper_name="self_written_python",
        command="python analysis/parse_outputs.py data/OUTCAR",
        script_path="analysis/parse_outputs.py",
        input_paths=["data/OUTCAR"],
        output_paths=["analysis/summary.csv", "figures/energy.png"],
        environment={"python": "3.13", "packages": ["pandas", "matplotlib"]},
    )

    manifest = result["manifest"]
    assert manifest["script_path"] == "analysis/parse_outputs.py"
    assert manifest["input_paths"] == ["data/OUTCAR"]
    assert manifest["output_paths"] == ["analysis/summary.csv", "figures/energy.png"]
    output = next(artifact for artifact in result["artifacts"] if artifact["name"] == "energy.png")
    output_lineage = get_lineage(output["artifact_id"], project_root=str(tmp_path))
    assert len(output_lineage["parent_artifacts"]) >= 2


def test_writing_claims_trace_to_evidence_artifacts_and_mark_speculation(tmp_path):
    init_workflow("custom", "writing", project_root=str(tmp_path))
    for rel_path, content in [
        ("literature/review_summary.md", "Claim evidence from literature.\n"),
        ("analysis/table.csv", "metric,value\nenergy,-1.0\n"),
        ("figures/energy.png", "png placeholder\n"),
        ("writing/draft.md", "Draft with traceable claims.\n"),
        ("writing/claim_map.json", "{}\n"),
    ]:
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    literature = register_artifact(
        "review_summary.md",
        "literature_review_summary",
        "literature_review",
        project_root=str(tmp_path),
        path="literature/review_summary.md",
    )
    table = register_artifact(
        "table.csv",
        "analysis_table",
        "analysis_visualization",
        project_root=str(tmp_path),
        path="analysis/table.csv",
    )
    figure = register_artifact(
        "energy.png",
        "figure",
        "analysis_visualization",
        project_root=str(tmp_path),
        path="figures/energy.png",
        parent_artifacts=[table["artifact_id"]],
    )
    claim_map = {
        "claims": [
            {"claim": "The computed energy is summarized in Figure 1.", "evidence_artifacts": [table["artifact_id"], figure["artifact_id"]], "speculative": False},
            {"claim": "A mechanistic explanation may involve bonding changes.", "evidence_artifacts": [literature["artifact_id"]], "speculative": True},
        ]
    }
    (tmp_path / "writing" / "claim_map.json").write_text(json.dumps(claim_map, indent=2), encoding="utf-8")
    draft = register_artifact(
        "draft.md",
        "scientific_draft",
        "writing",
        project_root=str(tmp_path),
        path="writing/draft.md",
        parent_artifacts=[literature["artifact_id"], table["artifact_id"], figure["artifact_id"]],
    )
    register_artifact(
        "claim_map.json",
        "claim_evidence_map",
        "writing",
        project_root=str(tmp_path),
        path="writing/claim_map.json",
        parent_artifacts=[draft["artifact_id"], literature["artifact_id"], table["artifact_id"], figure["artifact_id"]],
    )

    saved_claim_map = json.loads((tmp_path / "writing" / "claim_map.json").read_text(encoding="utf-8"))
    assert all(claim["evidence_artifacts"] for claim in saved_claim_map["claims"])
    assert saved_claim_map["claims"][1]["speculative"] is True
