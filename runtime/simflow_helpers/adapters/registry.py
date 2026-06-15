"""Metadata-only adapter contract registry."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from runtime.simflow_core.toolchains import (
    helper_capabilities_for_tool,
    normalize_tool_name,
    support_level_for_tool,
)


_ADAPTERS: dict[str, dict[str, Any]] = {
    "lammps": {
        "adapter_id": "lammps",
        "tool_id": "lammps",
        "aliases": ["lmp", "lammps"],
        "runtime_enabled": True,
        "recognized_files": [
            "in.lammps",
            "data.lammps",
            "log.lammps",
            "dump.lammpstrj",
            "restart.*",
        ],
        "supported_capabilities": [
            "static_input_inspection",
            "force_field_provenance_manifest",
            "dump_restart_manifest",
            "mlp_deployment_manifest",
            "trajectory_analysis_guidance",
            "evidence_handoff",
        ],
        "unsupported_capabilities": [
            "real_execution",
            "local_submit",
            "remote_execution",
            "hpc_submit",
        ],
        "evidence_roles_produced": [
            "lammps_input_inspection",
            "force_field_provenance_manifest",
            "dump_restart_manifest",
            "lammps_mlp_deployment_manifest",
        ],
        "claim_limits": [
            "LAMMPS adapter metadata does not imply execution readiness.",
            "MLP deployment evidence records how a model is referenced by LAMMPS only.",
            "No MLP training quality, validation adequacy, or production readiness claim is made.",
        ],
        "handoff_targets": ["simflow-mlp"],
    },
    "gpumd": {
        "adapter_id": "gpumd",
        "tool_id": "gpumd",
        "aliases": ["gpumd"],
        "runtime_enabled": True,
        "recognized_files": [
            "run.in",
            "model.xyz",
            "nep.txt",
            "thermo.out",
            "msd.out",
            "rdf.out",
            "hac.out",
            "kappa.out",
            "dos.out",
        ],
        "supported_capabilities": [
            "static_input_inspection",
            "manifest_generation",
            "selected_output_parsing",
            "evidence_handoff",
        ],
        "unsupported_capabilities": [
            "input_generation",
            "real_execution",
            "local_submit",
            "remote_execution",
            "hpc_submit",
        ],
        "evidence_roles_produced": [
            "gpumd_nep_input_inspection",
            "gpumd_nep_manifest",
            "gpumd_nep_output_parse_summary",
        ],
        "claim_limits": [
            "GPUMD remains tracked_only at tool level.",
            "No input generation, execution, submit, convergence, or production readiness claim is made.",
        ],
        "handoff_targets": ["simflow-mlp"],
    },
    "nep": {
        "adapter_id": "nep",
        "tool_id": "nep",
        "aliases": ["nep"],
        "runtime_enabled": True,
        "recognized_files": [
            "nep.in",
            "train.xyz",
            "test.xyz",
            "nep.txt",
            "loss.out",
            "energy_train.out",
            "energy_test.out",
            "force_train.out",
            "force_test.out",
            "stress_train.out",
            "stress_test.out",
            "descriptor.out",
        ],
        "supported_capabilities": [
            "static_input_inspection",
            "manifest_generation",
            "selected_output_parsing",
            "evidence_handoff",
        ],
        "unsupported_capabilities": [
            "input_generation",
            "real_execution",
            "local_submit",
            "remote_execution",
            "hpc_submit",
        ],
        "evidence_roles_produced": [
            "gpumd_nep_input_inspection",
            "gpumd_nep_manifest",
            "gpumd_nep_output_parse_summary",
            "model_metrics_summary",
        ],
        "claim_limits": [
            "NEP remains tracked_only at tool level.",
            "No training execution, model quality, transferability, or production readiness claim is made.",
        ],
        "handoff_targets": ["simflow-mlp"],
    },
}


def _alias_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for tool_id, adapter in _ADAPTERS.items():
        index[normalize_tool_name(tool_id)] = tool_id
        for alias in adapter.get("aliases", []):
            index[normalize_tool_name(alias)] = tool_id
    return index


def get_adapter(tool: str) -> dict[str, Any] | None:
    """Return adapter metadata for a tool without changing support policy."""
    tool_id = _alias_index().get(normalize_tool_name(tool))
    if not tool_id:
        return None
    adapter = deepcopy(_ADAPTERS[tool_id])
    adapter["tool_support_level"] = support_level_for_tool({}, adapter["tool_id"])
    adapter["capability_contract"] = helper_capabilities_for_tool(adapter["tool_id"])
    return adapter


def list_adapters() -> list[dict[str, Any]]:
    """Return all runtime-enabled adapter metadata records."""
    return [adapter for key in sorted(_ADAPTERS) if (adapter := get_adapter(key))]


def adapter_capabilities(tool: str) -> dict[str, Any]:
    """Return capability metadata with a stable empty result for unknown tools."""
    adapter = get_adapter(tool)
    if not adapter:
        normalized = normalize_tool_name(tool)
        return {
            "tool": normalized,
            "tool_support_level": support_level_for_tool({}, normalized),
            "supported_capabilities": [],
            "unsupported_capabilities": [],
            "evidence_roles_produced": [],
            "claim_limits": [],
            "handoff_targets": [],
        }
    return {
        "tool": adapter["tool_id"],
        "tool_support_level": adapter["tool_support_level"],
        "supported_capabilities": adapter["supported_capabilities"],
        "unsupported_capabilities": adapter["unsupported_capabilities"],
        "evidence_roles_produced": adapter["evidence_roles_produced"],
        "claim_limits": adapter["claim_limits"],
        "handoff_targets": adapter["handoff_targets"],
    }
