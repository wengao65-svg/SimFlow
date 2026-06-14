#!/usr/bin/env python3
"""Generate literature matrix artifacts from canonical research sources."""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.simflow_core.artifacts import register_artifact
from runtime.simflow_core.script_contracts import add_helper_recording_args, maybe_record_helper_run
from runtime.simflow_core.literature import enrich_research_sources
from runtime.simflow_core.state import read_state
from runtime.simflow_core.utils import generate_id


EMPTY_SOURCE_BUNDLE = {
    "bundle_version": "1.0",
    "counts": {"pdf": 0, "bibtex": 0, "doi": 0, "note": 0},
    "total_items": 0,
    "items": [],
}



def resolve_project_root_from_workflow_dir(workflow_dir: str) -> Path:
    """Resolve the project root from either a project root or .simflow path."""
    path = Path(workflow_dir).expanduser().resolve()
    return path.parent if path.name == ".simflow" else path



def build_literature_rows(research_sources: dict, metadata: dict, enrichment: dict | None = None) -> list[dict]:
    """Build matrix rows from the normalized research-source bundle."""
    metadata_by_source = (enrichment or {}).get("metadata_by_source", {})
    rows = []
    for item in research_sources.get("items", []):
        enriched = metadata_by_source.get(item["source_id"], {})
        rows.append({
            "source_id": item["source_id"],
            "source_type": item["type"],
            "label": item.get("label", ""),
            "locator": item.get("path") or item.get("doi") or "",
            "notes": item.get("text", "") if item.get("type") == "note" else "",
            "research_goal": metadata.get("research_goal", ""),
            "material": metadata.get("material", ""),
            "title": enriched.get("title", ""),
            "authors": enriched.get("authors", []),
            "year": enriched.get("year"),
            "journal": enriched.get("journal", enriched.get("venue", "")),
            "url": enriched.get("url", ""),
            "enrichment_source": enriched.get("source", ""),
        })
    return rows


def _source_locator(item: dict) -> str:
    return item.get("path") or item.get("doi") or item.get("text") or item.get("label", "")


def _access_status(item: dict) -> str:
    source_type = item.get("type")
    if source_type == "pdf":
        return "full_text_provided_by_user"
    if source_type == "doi":
        return "metadata_only_full_text_not_accessed"
    if source_type == "bibtex":
        return "citation_metadata_available"
    if source_type == "note":
        return "manual_note_no_external_full_text"
    return "unknown"


def _safe_note_name(source_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_id or "source").strip("_")
    return f"{safe or 'source'}.md"


def build_search_log(research_sources: dict, metadata: dict, enrichment: dict) -> dict:
    """Build source-traceable literature search log evidence."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_goal": metadata.get("research_goal", ""),
        "material": metadata.get("material", ""),
        "source_policy": "user_provided_or_agent_selected_sources",
        "provider_constraints": "none_fixed_by_simflow",
        "source_counts": research_sources.get("counts", EMPTY_SOURCE_BUNDLE["counts"]),
        "enrichment": {
            "backend": enrichment.get("backend"),
            "enabled": enrichment.get("enabled", False),
            "attempted": enrichment.get("attempted", 0),
            "enriched": enrichment.get("enriched", 0),
            "failed": enrichment.get("failed", 0),
            "errors": enrichment.get("errors", []),
        },
        "sources": [
            {
                "source_id": item.get("source_id"),
                "source_type": item.get("type"),
                "label": item.get("label", ""),
                "locator": _source_locator(item),
                "access_status": _access_status(item),
                "selection_reason": "seed_source_from_user_or_agent_intake",
            }
            for item in research_sources.get("items", [])
        ],
    }


def build_paper_note(row: dict, search_log: dict) -> str:
    """Build a source note that separates source claims from interpretation."""
    source = next(
        (item for item in search_log.get("sources", []) if item.get("source_id") == row.get("source_id")),
        {},
    )
    title = row.get("title") or row.get("label") or row.get("source_id")
    source_claim = row.get("notes") or "No direct source claim extracted yet."
    return "\n".join([
        f"# Paper Note: {title}",
        "",
        "## Source Metadata",
        f"- Source ID: {row.get('source_id')}",
        f"- Source type: {row.get('source_type')}",
        f"- Locator: {row.get('locator') or 'manual note'}",
        f"- Access status: {source.get('access_status', 'unknown')}",
        f"- Title: {row.get('title') or 'not available'}",
        f"- Year: {row.get('year') or 'not available'}",
        f"- Journal: {row.get('journal') or 'not available'}",
        "",
        "## Direct Source Claims",
        f"- {source_claim}",
        "",
        "## Agent Interpretation",
        "- Interpretation has not been added beyond the structured source inventory.",
        "",
        "## Follow-Up",
        "- Verify citation metadata and full-text access before relying on this source for final claims.",
        "",
    ])


def build_screening_record(matrix: dict) -> dict:
    """Build a lightweight source-screening record."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "screening_policy": "seed_sources_retained_for_traceable_review",
        "inclusion_criteria": [
            "source was provided by the user or captured during agent intake",
            "source locator can be traced",
        ],
        "exclusion_criteria": [
            "do not treat inaccessible full text as read",
            "do not treat unverified metadata as a verified citation",
        ],
        "records": [
            {
                "source_id": row.get("source_id"),
                "source_type": row.get("source_type"),
                "decision": "include_for_traceable_seed_review",
                "reason": "seed source retained for downstream evidence traceability",
            }
            for row in matrix.get("rows", [])
        ],
    }


def build_citation_map(matrix: dict, search_log: dict) -> dict:
    """Build citation metadata and access-status map."""
    access_by_source = {item.get("source_id"): item.get("access_status") for item in search_log.get("sources", [])}
    entries = []
    for row in matrix.get("rows", []):
        title = row.get("title") or row.get("label") or row.get("source_id")
        entries.append({
            "source_id": row.get("source_id"),
            "citation_key": row.get("source_id"),
            "source_type": row.get("source_type"),
            "locator": row.get("locator"),
            "title": title,
            "authors": row.get("authors", []),
            "year": row.get("year"),
            "journal": row.get("journal"),
            "url": row.get("url"),
            "access_status": access_by_source.get(row.get("source_id"), "unknown"),
            "verification_status": "enriched_metadata" if row.get("title") else "needs_citation_verification",
        })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }



def resolve_output_dir(project_root: Path, output_dir: str | None) -> Path:
    """Resolve the output directory for literature artifacts."""
    if not output_dir:
        return project_root / ".simflow" / "artifacts" / "literature"
    path = Path(output_dir).expanduser()
    return path if path.is_absolute() else project_root / path



def generate_literature_matrix(workflow_dir: str, output_dir: str = None, enrich_backend: str | None = None) -> dict:
    """Generate literature matrix JSON and CSV artifacts."""
    project_root = resolve_project_root_from_workflow_dir(workflow_dir)
    state = read_state(project_root=str(project_root), state_file="workflow.json")
    if not state:
        return {"status": "error", "message": "No workflow state found"}

    metadata = read_state(project_root=str(project_root), state_file="metadata.json")
    research_sources = metadata.get("research_sources") or EMPTY_SOURCE_BUNDLE
    enrichment = enrich_research_sources(research_sources, backend=enrich_backend) if enrich_backend else {
        "backend": None,
        "enabled": False,
        "attempted": 0,
        "enriched": 0,
        "failed": 0,
        "metadata_by_source": {},
        "errors": [],
    }
    rows = build_literature_rows(research_sources, metadata, enrichment)
    search_log = build_search_log(research_sources, metadata, enrichment)

    matrix = {
        "matrix_id": generate_id("litmatrix"),
        "workflow_id": state.get("workflow_id", metadata.get("workflow_id", "unknown")),
        "workflow_type": metadata.get("workflow_type", state.get("workflow_type", "dft")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_goal": metadata.get("research_goal", "Not specified"),
        "material": metadata.get("material", "Not specified"),
        "software": metadata.get("software", "custom"),
        "source_counts": research_sources.get("counts", EMPTY_SOURCE_BUNDLE["counts"]),
        "row_count": len(rows),
        "enrichment": {
            "backend": enrichment.get("backend"),
            "enabled": enrichment.get("enabled", False),
            "attempted": enrichment.get("attempted", 0),
            "enriched": enrichment.get("enriched", 0),
            "failed": enrichment.get("failed", 0),
            "errors": enrichment.get("errors", []),
        },
        "rows": rows,
    }

    literature_dir = resolve_output_dir(project_root, output_dir)
    literature_dir.mkdir(parents=True, exist_ok=True)
    notes_dir = literature_dir / "paper_notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    search_log_path = literature_dir / "search_log.json"
    json_path = literature_dir / "literature_matrix.json"
    csv_path = literature_dir / "literature_matrix.csv"
    screening_path = literature_dir / "screening_record.json"
    citation_map_path = literature_dir / "citation_map.json"

    search_log_path.write_text(json.dumps(search_log, indent=2, ensure_ascii=False), encoding="utf-8")
    json_path.write_text(json.dumps(matrix, indent=2, ensure_ascii=False), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_id", "source_type", "label", "locator", "notes", "research_goal", "material",
                "title", "authors", "year", "journal", "url", "enrichment_source",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    paper_note_paths = []
    for row in rows:
        note_path = notes_dir / _safe_note_name(row.get("source_id", "source"))
        note_path.write_text(build_paper_note(row, search_log), encoding="utf-8")
        paper_note_paths.append(note_path)
    screening_record = build_screening_record(matrix)
    citation_map = build_citation_map(matrix, search_log)
    screening_path.write_text(json.dumps(screening_record, indent=2, ensure_ascii=False), encoding="utf-8")
    citation_map_path.write_text(json.dumps(citation_map, indent=2, ensure_ascii=False), encoding="utf-8")

    search_registry_path = str(search_log_path.resolve().relative_to(project_root)) if search_log_path.resolve().is_relative_to(project_root) else str(search_log_path.resolve())
    json_registry_path = str(json_path.resolve().relative_to(project_root)) if json_path.resolve().is_relative_to(project_root) else str(json_path.resolve())
    csv_registry_path = str(csv_path.resolve().relative_to(project_root)) if csv_path.resolve().is_relative_to(project_root) else str(csv_path.resolve())
    screening_registry_path = str(screening_path.resolve().relative_to(project_root)) if screening_path.resolve().is_relative_to(project_root) else str(screening_path.resolve())
    citation_registry_path = str(citation_map_path.resolve().relative_to(project_root)) if citation_map_path.resolve().is_relative_to(project_root) else str(citation_map_path.resolve())

    search_artifact = register_artifact(
        "search_log.json",
        "search_log",
        "literature_review",
        project_root=str(project_root),
        path=search_registry_path,
        parameters={"source_count": research_sources.get("total_items", len(rows))},
        software=metadata.get("software"),
        metadata={"evidence_key": "search_log"},
    )
    json_artifact = register_artifact(
        "literature_matrix.json",
        "literature_matrix",
        "literature_review",
        project_root=str(project_root),
        path=json_registry_path,
        parent_artifacts=[search_artifact["artifact_id"]],
        parameters={"row_count": len(rows)},
        software=metadata.get("software"),
    )
    csv_artifact = register_artifact(
        "literature_matrix.csv",
        "literature_matrix_csv",
        "literature_review",
        project_root=str(project_root),
        path=csv_registry_path,
        parent_artifacts=[json_artifact["artifact_id"]],
        parameters={"row_count": len(rows)},
        software=metadata.get("software"),
    )
    note_artifacts = []
    for note_path in paper_note_paths:
        note_registry_path = str(note_path.resolve().relative_to(project_root)) if note_path.resolve().is_relative_to(project_root) else str(note_path.resolve())
        note_artifacts.append(register_artifact(
            note_path.name,
            "paper_notes",
            "literature_review",
            project_root=str(project_root),
            path=note_registry_path,
            parent_artifacts=[search_artifact["artifact_id"], json_artifact["artifact_id"]],
            software=metadata.get("software"),
            metadata={"evidence_key": "paper_notes"},
        ))
    screening_artifact = register_artifact(
        "screening_record.json",
        "screening_record",
        "literature_review",
        project_root=str(project_root),
        path=screening_registry_path,
        parent_artifacts=[search_artifact["artifact_id"], json_artifact["artifact_id"]],
        software=metadata.get("software"),
        metadata={"evidence_key": "screening_record"},
    )
    citation_artifact = register_artifact(
        "citation_map.json",
        "citation_map",
        "literature_review",
        project_root=str(project_root),
        path=citation_registry_path,
        parent_artifacts=[search_artifact["artifact_id"], json_artifact["artifact_id"]],
        software=metadata.get("software"),
        metadata={"evidence_key": "citation_map"},
    )

    return {
        "status": "success",
        "matrix": matrix,
        "output_files": {
            "search_log": str(search_log_path),
            "json": str(json_path),
            "csv": str(csv_path),
            "screening_record": str(screening_path),
            "citation_map": str(citation_map_path),
            "paper_notes": [str(path) for path in paper_note_paths],
        },
        "artifacts": [
            search_artifact,
            json_artifact,
            csv_artifact,
            *note_artifacts,
            screening_artifact,
            citation_artifact,
        ],
    }



def main():
    parser = argparse.ArgumentParser(description="Generate literature matrix artifacts")
    parser.add_argument("--workflow-dir", required=True, help="Path to .simflow directory")
    parser.add_argument("--output-dir", help="Optional output directory for literature artifacts")
    parser.add_argument("--enrich-backend", help="Optional literature backend for DOI enrichment")
    add_helper_recording_args(parser, default_stage="literature_review")
    args = parser.parse_args()

    try:
        result = generate_literature_matrix(args.workflow_dir, args.output_dir, args.enrich_backend)
        output_paths = []
        for value in result.get("output_files", {}).values():
            if isinstance(value, list):
                output_paths.extend(value)
            else:
                output_paths.append(value)
        result = maybe_record_helper_run(
            args=args,
            result=result,
            script_path=Path(__file__).resolve(),
            helper_name="generate_literature_matrix",
            output_paths=output_paths,
        )
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
