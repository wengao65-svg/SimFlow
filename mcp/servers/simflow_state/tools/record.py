"""Tool: append one logical SimFlow project record."""

from runtime.simflow_core.migration import MigrationError, apply_migration
from runtime.simflow_core.records import record_event
from runtime.simflow_core.state import ProjectRootError


def execute(params: dict) -> dict:
    project_root = params.get("project_root")
    if not project_root:
        return {"status": "error", "message": "project_root is required"}
    try:
        if params.get("kind") == "migration":
            data = apply_migration(
                project_root,
                migration_report_hash=params.get("migration_report_hash", ""),
                confirm_migration=params.get("confirm_migration") is True,
                summary=params.get("summary", "Index legacy SimFlow state"),
            )
            return {"status": "success", "project_root": project_root, "data": data}
        data = record_event(
            project_root,
            kind=params.get("kind", ""),
            summary=params.get("summary", ""),
            status=params.get("status"),
            stage=params.get("stage"),
            run_id=params.get("run_id"),
            goal=params.get("goal"),
            next_action=params.get("next_action"),
            artifacts=params.get("artifacts"),
            parent_ids=params.get("parent_ids"),
            details=params.get("details"),
        )
    except (MigrationError, ProjectRootError, TypeError, ValueError) as error:
        return {"status": "error", "message": str(error)}
    return {"status": "success", "project_root": project_root, "data": data}
