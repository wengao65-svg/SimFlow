#!/usr/bin/env python3
"""Tests for metadata-only helper adapter contracts."""

import json
from pathlib import Path

from runtime.simflow_helpers.adapters import adapter_capabilities, get_adapter, list_adapters
from runtime.simflow_helpers.adapters.registry import load_adapter_contract

ROOT = Path(__file__).resolve().parents[2]


def test_adapter_registry_marks_gpumd_nep_helper_supported_with_gated_execution():
    gpumd = get_adapter("gpumd")
    nep = get_adapter("nep")

    assert gpumd is not None
    assert nep is not None
    assert gpumd["tool_support_level"] == "helper_supported"
    assert nep["tool_support_level"] == "helper_supported"
    assert "static_input_inspection" in gpumd["supported_capabilities"]
    assert "input_generation" in gpumd["supported_capabilities"]
    assert "input_validation" in nep["supported_capabilities"]
    assert "real_execution" in gpumd["unsupported_capabilities"]
    assert "hpc_submit" in nep["unsupported_capabilities"]


def test_adapter_registry_exposes_lammps_mlp_deployment_metadata():
    lammps = get_adapter("lmp")

    assert lammps is not None
    assert lammps["tool_id"] == "lammps"
    assert lammps["tool_support_level"] == "helper_supported"
    assert "lammps_mlp_deployment_manifest" in lammps["evidence_roles_produced"]
    assert lammps["handoff_targets"] == ["simflow-mlp"]
    assert "real_execution" in lammps["unsupported_capabilities"]


def test_unknown_adapter_returns_empty_capability_record():
    capabilities = adapter_capabilities("bespoke-engine")

    assert capabilities["tool"] == "bespoke_engine"
    assert capabilities["tool_support_level"] == "unknown"
    assert capabilities["supported_capabilities"] == []
    assert capabilities["evidence_roles_produced"] == []


def test_list_adapters_is_metadata_only_and_runtime_limited():
    adapters = {adapter["tool_id"]: adapter for adapter in list_adapters()}

    assert set(adapters) == {"gpumd", "lammps", "nep"}
    for adapter in adapters.values():
        assert adapter["runtime_enabled"] is True
        assert "recognized_files" in adapter
        assert "claim_limits" in adapter


def test_active_adapter_registry_is_json_backed():
    contract = load_adapter_contract()
    active = {
        item["tool_id"]: item
        for item in contract["adapters"]
        if item["runtime_enabled"] is True
    }

    assert contract["schema_version"] == "simflow.helper_adapters.v1"
    assert "never execute tools" in contract["policy"]
    assert set(active) == {"gpumd", "lammps", "nep"}
    assert active["gpumd"]["unsupported_capabilities"] == ["real_execution", "local_submit", "remote_execution", "hpc_submit"]


def test_ecosystem_roadmap_fixtures_are_not_active_adapters_or_skills():
    roadmap = json.loads((ROOT / "workflow" / "toolchains" / "adapter_roadmap.json").read_text(encoding="utf-8"))
    reviews = json.loads((ROOT / "workflow" / "toolchains" / "adapter_enablement_reviews.json").read_text(encoding="utf-8"))
    reviews_by_tool = {item["tool_id"]: item for item in reviews["reviews"]}

    assert roadmap["schema_version"] == "simflow.adapter_roadmap.v1"
    assert reviews["schema_version"] == "simflow.adapter_enablement_reviews.v1"
    assert all(candidate["runtime_enabled"] is False for candidate in roadmap["candidates"])
    assert "not active runtime adapters" in roadmap["policy"]
    assert "does not execute tools" in reviews["policy"]
    for candidate in roadmap["candidates"]:
        review = reviews_by_tool[candidate["tool_id"]]
        assert review["status"] == "candidate_only"
        assert review["requested_runtime_enabled"] is False
        assert get_adapter(candidate["tool_id"]) is None
        if candidate["tool_id"] != "quantum_espresso":
            assert not (ROOT / "skills" / f"simflow-{candidate['tool_id']}").exists()
