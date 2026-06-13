#!/usr/bin/env python3
"""Tests for shared toolchain support semantics."""

from pathlib import Path

from runtime.simflow_core.toolchains import (
    build_actual_tool_used,
    build_toolchain_plan,
    classify_tool_support,
    normalize_tool_name,
    support_level_for_tool,
)
from runtime.simflow_core.workflow import list_recipes, load_recipe


ROOT = Path(__file__).resolve().parents[2]


def test_tool_support_levels_are_shared_and_non_blocking():
    support = classify_tool_support(["vasp", "cp2k", "lammps", "gromacs", "gpumd", "bespoke"])

    assert support["builtin_helpers"] == ["vasp", "cp2k", "lammps"]
    assert support["tracked_only"] == ["gromacs", "gpumd"]
    assert support["unknown"] == ["bespoke"]
    assert support["support_levels"]["vasp"] == "helper_supported"
    assert support["support_levels"]["gromacs"] == "tracked_only"
    assert support["support_levels"]["bespoke"] == "unknown"


def test_known_aliases_normalize_before_support_classification():
    assert normalize_tool_name("QE") == "quantum_espresso"
    assert normalize_tool_name("Quantum-ESPRESSO") == "quantum_espresso"

    support = classify_tool_support(["quantum_espresso"])

    assert support["tracked_only"] == ["quantum_espresso"]
    assert support_level_for_tool({"software_support": support}, "qe") == "tracked_only"


def test_all_recipe_applicable_software_has_known_support_level():
    unknown_by_recipe = {}
    for recipe_name in list_recipes():
        recipe = load_recipe(recipe_name)
        tools = [normalize_tool_name(tool) for tool in recipe.get("applicable_software", [])]
        support = classify_tool_support(tools)
        if support["unknown"]:
            unknown_by_recipe[recipe_name] = support["unknown"]

    assert unknown_by_recipe == {}


def test_build_toolchain_plan_uses_recipe_activity_metadata_without_support_logic():
    plan = build_toolchain_plan(
        "mlp_md",
        "gpumd",
        ["gpumd", "cp2k", "vasp", "nep", "neptrainkit"],
    )

    assert plan["activities"]["labeling"] == ["cp2k", "vasp"]
    assert plan["activities"]["training"] == ["gpumd", "nep"]
    assert plan["activities"]["selection"] == ["neptrainkit"]
    assert "support_levels" not in plan


def test_build_toolchain_plan_defaults_for_non_activity_recipes():
    plan = build_toolchain_plan("dft", "quantum_espresso", ["quantum_espresso"])

    assert plan["activities"] == {"primary": ["quantum_espresso"]}


def test_build_actual_tool_used_uses_shared_support_levels():
    contract = {
        "software": "gromacs",
        "helper_support": classify_tool_support(["gromacs"]),
    }

    actual = build_actual_tool_used(contract, "gromacs", command="gmx mdrun")

    assert actual == {
        "name": "gromacs",
        "support_level": "tracked_only",
        "command": "gmx mdrun",
        "version": None,
        "environment": None,
    }


def test_proposal_scripts_do_not_redefine_toolchain_support_logic():
    forbidden = [
        "SUPPORTED_HELPER_SOFTWARE",
        "TRACKED_ONLY_SOFTWARE",
        "def _software_support",
        "def _toolchain_plan",
    ]
    for rel_path in (
        "skills/simflow-proposal/scripts/generate_proposal.py",
        "runtime/simflow_core/proposals.py",
    ):
        source = (ROOT / rel_path).read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in source, f"{rel_path} must use runtime.simflow_core.toolchains for {pattern}"


def test_recipes_do_not_define_support_level_fields():
    forbidden_fields = {"tracked_only_software", "helper_supported_software", "unsupported_software"}
    for recipe_name in list_recipes():
        recipe = load_recipe(recipe_name)
        present = forbidden_fields & set(recipe)
        assert not present, f"{recipe_name} recipe must not define support fields: {sorted(present)}"
