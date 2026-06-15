#!/usr/bin/env python3
"""Tests for metadata-only helper adapter contracts."""

import json
from pathlib import Path

from runtime.simflow_helpers.adapters import adapter_capabilities, get_adapter, list_adapters

ROOT = Path(__file__).resolve().parents[2]


def test_adapter_registry_keeps_gpumd_nep_tracked_only():
    gpumd = get_adapter("gpumd")
    nep = get_adapter("nep")

    assert gpumd is not None
    assert nep is not None
    assert gpumd["tool_support_level"] == "tracked_only"
    assert nep["tool_support_level"] == "tracked_only"
    assert "static_input_inspection" in gpumd["supported_capabilities"]
    assert "input_generation" in gpumd["unsupported_capabilities"]
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


def test_ecosystem_roadmap_fixtures_are_not_active_adapters_or_skills():
    roadmap = json.loads((ROOT / "workflow" / "toolchains" / "adapter_roadmap.json").read_text(encoding="utf-8"))

    assert roadmap["schema_version"] == "simflow.adapter_roadmap.v1"
    assert all(candidate["runtime_enabled"] is False for candidate in roadmap["candidates"])
    assert "not active runtime adapters" in roadmap["policy"]
    for candidate in roadmap["candidates"]:
        assert get_adapter(candidate["tool_id"]) is None
    assert not (ROOT / "skills" / "simflow-deepmd").exists()
    assert not (ROOT / "skills" / "simflow-mace").exists()
