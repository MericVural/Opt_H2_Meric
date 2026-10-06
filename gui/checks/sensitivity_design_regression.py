"""OAT composition tests; native annual problems are preflighted, never solved."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

STAGE = Path(os.environ.get("H2_GUI_SOURCE_ROOT", Path(__file__).resolve().parents[2])).resolve()
sys.path.insert(0, str(STAGE))
from gui import model_adapter, sensitivity_design as design
from gui.case_study_registry import load_registry

REPO = Path(os.environ.get("H2_REPO_ROOT", r"C:\Forschungsarbeit\Opt_H2_Meric-h2"))
MODEL_PYTHON = Path(os.environ.get("H2_MODEL_PYTHON", r"C:\Users\meric\anaconda3\envs\h2-model\python.exe"))
from gui.checks.inventory_fixture import BEFORE
UNITS = BEFORE["native_parameter_units"]


@pytest.fixture
def site(tmp_path):
    refs = {}
    for profile, weights in (("D0", [1, 1, 1, 1]), ("D1", [0, 2, 2, 0]), ("D2", [0, 0, 4, 0])):
        path = tmp_path / (profile + ".csv")
        pd.DataFrame({"timestamp": ["a", "b", "c", "d"],
                      "electricity_price": [1, 2, 3, 4], "h2_demand": weights}).to_csv(path, index=False)
        metadata = tmp_path / (profile + ".json")
        metadata.write_text("{}", encoding="utf-8")
        refs[profile] = SimpleNamespace(path=path, metadata_path=metadata)
    return SimpleNamespace(study_id="eu_2024", site_id="hamburg_moorburg",
        runner_kind="eu", can_run=True, historical=False, profiles=refs,
        design_path=tmp_path / "design.json", year_roles={"study_operation_year": 2024}, metadata={})


@pytest.fixture
def native_boundary(monkeypatch):
    calls = []
    monkeypatch.setattr(model_adapter, "supported_parameters", lambda *args, **kwargs: UNITS)
    def single(**kwargs):
        calls.append(("single", kwargs))
        return {"study_id": kwargs["study_id"], "site_id": kwargs["site_id"],
                "profile_id": kwargs["profile_id"], "solver": kwargs["solver"],
                "kind": "single", "scenarios": list(kwargs["scenarios"]),
                "variants": [], "repo_root": "test_native_root", "model_python": "native_python",
                "optimization_count": len(kwargs["scenarios"]),
                "input": {"path": str(kwargs["input_csv"])}}
    def sensitivity(**kwargs):
        variants = kwargs.pop("variants")
        child = single(**kwargs)
        calls[-1] = ("sensitivity", {**kwargs, "variants": variants})
        child.update(kind="sensitivity", variants=variants,
                     optimization_count=(1 + len(variants)) * len(kwargs["scenarios"]))
        return child
    monkeypatch.setattr(model_adapter, "build_single_plan", single)
    monkeypatch.setattr(model_adapter, "build_sensitivity_plan", sensitivity)
    return calls


def variants(values=(.5, 1.5)):
    return [{"parameter": "h2_demand_multiplier", "value": value,
             "source": "explicit_test", "note": "OAT demand quantity", "label": str(value)}
            for value in values]


@pytest.mark.parametrize("study_id,site_id,kind", [("eu_2024", "hamburg_moorburg", "eu"),
                                                    ("eu_2024", "huelva_la_rabida", "eu"),
                                                    ("namibia", "namibia", "legacy")])
def test_all_preexisting_numeric_parameters_preserved(study_id, site_id, kind):
    old = BEFORE["studies"][study_id]["sites"][site_id]
    site = SimpleNamespace(runner_kind=kind, profiles=old["profiles"])
    current = design.sensitivity_parameter_choices(UNITS, site)
    assert {key: value for key, value in current.items() if key != design.PROFILE_PARAMETER} == old["numeric_sensitivity_parameters"]
    assert len(old["numeric_sensitivity_parameters"]) == 11
    assert (design.PROFILE_PARAMETER in current) == (len(old["profiles"]) > 1)
    assert "uniform_real_wacc_fraction" not in current


def test_mixed_profile_numeric_design_is_sum_not_factorial(site, native_boundary):
    request = design.build_oat_profile_plan(REPO, site, ["D0"],
        ["reference", "red_monthly", "red_hourly"], variants=variants(),
        profile_levels=["D0", "D1", "D2"])
    assert request["optimization_count"] == 15  # (1 baseline + 2 numeric + 2 profiles) * 3
    assert [call[0] for call in native_boundary] == ["sensitivity", "single", "single"]
    assert [child["profile_id"] for child in request["plans"]] == ["D0", "D1", "D2"]
    assert [len(child["variants"]) for child in request["plans"]] == [2, 0, 0]
    assert request["gui_oat_design"]["numeric_variants_crossed_with_profile_levels"] is False
    assert request["gui_oat_design"]["profile_input_receipt"]["annual_h2_requested_kg"] == 4
    assert request["gui_oat_design"]["profile_input_receipt"]["unchanged_hourly_input_columns"] == ["timestamp", "electricity_price"]


def test_existing_three_context_quantity_experiment_remains_45_cases_per_site(site, native_boundary):
    request = design.build_oat_profile_plan(REPO, site, ["D0", "D1", "D2"],
        ["reference", "red_monthly", "red_hourly"], variants=variants((.5, .75, 1.25, 1.5)),
        profile_levels=["D0", "D1", "D2"])
    assert request["optimization_count"] == 45
    assert len(request["plans"]) == 3
    assert all(child["kind"] == "sensitivity" for child in request["plans"])
    assert request["gui_oat_design"]["profile_only_levels"] == []


def test_category_only_uses_one_fresh_native_baseline_per_profile(site, native_boundary):
    request = design.build_oat_profile_plan(REPO, site, ["D0"], ["reference", "off_grid"],
                                          profile_levels=["D0", "D1", "D2"])
    assert request["optimization_count"] == 6
    assert len(native_boundary) == 3
    assert all(child["kind"] == "single" and not child["variants"] for child in request["plans"])
    assert all(child["scenarios"] == ["reference", "off_grid"] for child in request["plans"])
    assert [child["gui_oat_design"]["role"] for child in request["plans"]] == ["numeric_base_context", "profile_only_level", "profile_only_level"]


def test_selected_numeric_baselines_are_not_duplicated_by_profile_levels(site, native_boundary):
    request = design.build_oat_profile_plan(REPO, site, ["D0", "D1"], ["reference"],
        variants=variants(), profile_levels=["D1", "D2"])
    assert request["optimization_count"] == 7
    assert [child["profile_id"] for child in request["plans"]] == ["D0", "D1", "D2"]
    assert [len(child["variants"]) for child in request["plans"]] == [2, 2, 0]


def test_two_solver_comparison_retains_inputs_source_site_scenarios(site, native_boundary):
    request = design.build_oat_profile_plan(REPO, site, ["D0"], ["red_hourly"],
        variants=variants(), profile_levels=["D0", "D2"], compare_solvers=True)
    assert request["optimization_count"] == 8
    assert [child["solver"] for child in request["plans"]] == ["scipy-highs", "scipy-highs", "gurobi", "gurobi"]
    for _, options in native_boundary:
        assert options["study_id"] == "eu_2024"
        assert options["site_id"] == "hamburg_moorburg"
        assert options["runner_kind"] == "eu"
        assert options["design_json"] == site.design_path
        assert options["source_metadata"] == site.profiles[options["profile_id"]].metadata_path
        assert options["scenarios"] == ["red_hourly"]
    assert all(child["gui_context"]["year_roles"] == site.year_roles for child in request["plans"])


@pytest.mark.parametrize("bases,scenarios,levels,match", [
    ([], ["reference"], ["D0", "D1"], "Basis"),
    (["D0"], [], ["D0", "D1"], "Szenario"),
    (["D0", "D0"], ["reference"], ["D1"], "Doppelte"),
    (["D0"], ["reference", "reference"], ["D1"], "Doppelte"),
    (["D0"], ["reference"], ["D1", "D1"], "Doppelte"),
    (["D0"], ["reference"], ["D0"], "zwei"),
    (["D0"], ["reference"], [], "Sensitivitätsparameter"),
])
def test_invalid_scope_rejected(bases, scenarios, levels, match):
    with pytest.raises(ValueError, match=match):
        design.oat_profile_scope(bases, scenarios, [], levels)


def test_unknown_profile_rejected_before_native_plan(site, native_boundary):
    with pytest.raises(ValueError, match="Standort"):
        design.build_oat_profile_plan(REPO, site, ["D0"], ["reference"], profile_levels=["D8"])
    assert not native_boundary


@pytest.mark.parametrize("change,match", [("price", "übrige"), ("annual", "Jahresmenge"),
                                        ("negative", "ungültige"), ("timestamp", "übrige")])
def test_category_oat_input_intervention_is_one_factor(site, native_boundary, change, match):
    frame = pd.read_csv(site.profiles["D1"].path)
    if change == "price":
        frame.loc[0, "electricity_price"] = 99
    elif change == "annual":
        frame["h2_demand"] *= 2
    elif change == "negative":
        frame.loc[0, "h2_demand"] = -1
        frame.loc[1, "h2_demand"] = 3
    else:
        frame.loc[0, "timestamp"] = "other"
    frame.to_csv(site.profiles["D1"].path, index=False)
    with pytest.raises(ValueError, match=match):
        design.build_oat_profile_plan(REPO, site, ["D0"], ["reference"], profile_levels=["D0", "D1"])
    assert not native_boundary


@pytest.mark.parametrize("parameter", ["uniform_real_wacc_fraction", "electricity_price_eur_per_mwh", "unsupported"])
def test_study_unsupported_numeric_parameter_rejected(site, native_boundary, parameter):
    with pytest.raises(ValueError, match="Fallstudie"):
        design.build_oat_profile_plan(REPO, site, ["D0"], ["reference"],
                                      variants=[{"parameter": parameter, "value": 1}])
    assert not native_boundary


def test_categorical_parameter_never_forwarded_to_numeric_override():
    with pytest.raises(ValueError, match="separat"):
        design.oat_profile_scope(["D0"], ["reference"],
            [{"parameter": design.PROFILE_PARAMETER, "value": "D1"}], ["D0", "D1"])


def test_namibia_archived_wacc_forwarded_explicitly(site, native_boundary):
    site.runner_kind = "legacy"
    site.study_id = "namibia"
    site.site_id = "namibia"
    site.profiles = {"D0": site.profiles["D0"]}
    site.historical = True
    site.metadata = {"baseline_metadata": {"model_parameters": {
        "technologies.pv.real_wacc_fraction": {"value": .11, "source": "archived_wacc", "note": "proxy"}}}}
    request = design.build_oat_profile_plan(REPO, site, ["D0"], ["reference"],
        variants=[{"parameter": "electricity_price_eur_per_mwh", "value": 50}])
    options = native_boundary[0][1]
    assert options["uniform_wacc_percent"] == 11
    assert options["uniform_wacc_source"] == "archived_wacc"
    assert options["source_note"] == "proxy"
    assert "design_json" not in options
    assert request["plans"][0]["gui_context"]["historical"] is True


def test_scope_copies_gui_variants_without_mutating_editor_state():
    selected = variants()
    scope = design.oat_profile_scope(["D0"], ["reference"], selected)
    scope["variants"][0]["value"] = 99
    assert selected[0]["value"] == .5


@pytest.mark.parametrize("site_id", ["hamburg_moorburg", "huelva_la_rabida"])
def test_actual_source_bound_profile_oat_delegates_to_existing_native_preflight(site_id):
    registry = load_registry(REPO, REPO / "gui" / "case_studies.json")
    site = registry.get_site("eu_2024", site_id)
    request = design.build_oat_profile_plan(REPO, site, ["D0"], ["reference"],
        variants=variants(), profile_levels=["D0", "D1", "D2"], model_python=MODEL_PYTHON)
    assert request["optimization_count"] == 5
    assert [len(child["variants"]) for child in request["plans"]] == [2, 0, 0]
    assert all(child["expected_hours"] == 8784 for child in request["plans"])
    assert all(child["input_context"]["annual_h2_requested_kg"] == pytest.approx(3650000)
               for child in request["plans"])
    from gui.jobs import _command
    for child in request["plans"]:
        child.update(cases={"path": "cases.csv"}, output_directory="isolated_new_output")
        command = _command(child)
        assert command[1] == str(REPO / "run_h2_sensitivity.py")
        assert command[command.index("--eu-site") + 1] == site_id
        assert command[command.index("--eu-design") + 1] == str(site.design_path)
        assert "--require-separate-emission-factors" in command
        assert command[command.index("--emission-factor-metadata") + 1] == str(site.profiles[child["profile_id"]].metadata_path)
        assert "--h2-delivery-profile" not in command


def test_actual_90_case_experiment_can_still_be_planned_with_three_basis_contexts():
    registry = load_registry(REPO, REPO / "gui" / "case_studies.json")
    site = registry.get_site("eu_2024", "hamburg_moorburg")
    request = design.build_oat_profile_plan(REPO, site, ["D0", "D1", "D2"],
        ["reference", "red_monthly", "red_hourly"],
        variants=variants((.5, .75, 1.25, 1.5)), model_python=MODEL_PYTHON)
    assert request["optimization_count"] == 45
    assert len(request["plans"]) == 3
    assert all(len(child["variants"]) == 4 for child in request["plans"])
    assert request["gui_oat_design"]["profile_input_receipt"] is None


def test_actual_24h_mixed_numeric_profile_job_uses_native_worker_and_own_validations(tmp_path):
    """Four OAT cases * three scenarios; never a 2-profile factorial design."""
    import numpy as np
    from gui.jobs import prepare_job, run_job
    t = np.arange(24)
    source = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=24, freq="h", tz="UTC"),
        "pv_capacity_factor": np.maximum(0, np.sin((t - 6) * np.pi / 12)) * .75,
        "wind_capacity_factor": .25 + .1 * np.cos(t * np.pi / 12),
        "electricity_price": 80. + 40. * np.cos(t * np.pi / 12),
        "grid_emission_factor": 220., "h2_demand": 10000. / 24,
    })
    refs = {}
    for profile in ("D0", "D1"):
        frame = source.copy()
        if profile == "D1":
            frame["h2_demand"] = np.where((t >= 8) & (t < 20), 10000. / 12, 0.)
        path = tmp_path / (profile + ".csv")
        frame.to_csv(path, index=False)
        metadata = tmp_path / (profile + ".metadata.json")
        metadata.write_text(json.dumps({"fixture_profile": profile}), encoding="utf-8")
        refs[profile] = SimpleNamespace(path=path, metadata_path=metadata)
    fixture_site = SimpleNamespace(study_id="synthetic_oat_regression", site_id="synthetic_site",
        runner_kind="legacy", can_run=True, historical=False, profiles=refs,
        design_path=None, year_roles={"profile_index_year": 2025}, metadata={
            "baseline_metadata": {"model_parameters": {"technologies.pv.real_wacc_fraction": {
                "value": .11, "source": "Explicit 11 percent 24-hour regression fixture", "note": "synthetic test"}}}})
    numeric = [{"parameter": "pv_capex_eur_per_kw", "value": cost,
                "source": "Synthetic OAT regression assumption", "note": "One PV CAPEX intervention",
                "label": str(cost)} for cost in (690.75, 1151.25)]
    plan = design.build_oat_profile_plan(REPO, fixture_site, ["D0"],
        ["reference", "red_monthly", "red_hourly"], variants=numeric,
        profile_levels=["D0", "D1"], model_python=MODEL_PYTHON)
    assert plan["optimization_count"] == 12
    job = prepare_job(plan, tmp_path / "jobs", python_executable=MODEL_PYTHON)
    state = run_job(job)
    assert state["state"] == "completed", state
    assert state["completed_cases"] == state["total_cases"] == 12
    assert state["validation_status"] == "passed"
    record = json.loads((job / "plan.json").read_text(encoding="utf-8"))
    assert [child["profile_id"] for child in record["execution_plans"]] == ["D0", "D1"]
    assert [len(child["variants"]) for child in record["execution_plans"]] == [2, 0]
    observations = []
    for child in record["execution_plans"]:
        output = Path(child["output_directory"])
        table = pd.read_csv(output / "sensitivity_comparison.csv")
        assert len(table) == (9 if child["profile_id"] == "D0" else 3)
        assert table["solver_status"].eq("optimal").all()
        assert table["sensitivity_parameter"].eq("baseline").sum() == 3
        if child["profile_id"] == "D1":
            assert table["sensitivity_parameter"].eq("baseline").all()
        reports = list((output / "runs").glob("*/validation/validation_report.json"))
        assert len(reports) == (3 if child["profile_id"] == "D0" else 1)
        for report in reports:
            validation = json.loads(report.read_text(encoding="utf-8"))
            assert validation["all_checks_passed"] is True
        for _, row in table.iterrows():
            result = output / row["result_directory"]
            native = json.loads((result / "run_metadata.json").read_text(encoding="utf-8"))
            requested = native.get("sensitivity_override", {})
            frame = pd.read_csv(result / "validated_input.csv")
            if child["profile_id"] == "D1":
                assert frame.loc[(t < 8) | (t >= 20), "h2_demand"].eq(0).all()
                assert not requested or requested.get("parameter") != "pv_capex_eur_per_kw"
                assert native["model_parameters"]["technologies.pv.capex_eur_per_kw"]["value"] == pytest.approx(921)
            else:
                assert frame["h2_demand"].eq(frame["h2_demand"].iloc[0]).all()
        observations.append({"profile": child["profile_id"], "native_cases": len(table),
                             "own_independent_reports": len(reports), "all_optimal": True})
    evidence = {"status": "passed", "job_directory": str(job),
        "annual_optimizer_calls": 0, "small_24h_optimizer_calls": 12,
        "optimization_count": 12, "numeric_variants_crossed_with_profile_levels": False,
        "validation_status": state["validation_status"], "profiles": observations}
    evidence_root = Path(os.environ.get("H2_GUI_TEST_EVIDENCE_ROOT", tmp_path))
    evidence_root.mkdir(parents=True, exist_ok=True)
    (evidence_root / "PROFILE_OAT_NATIVE_JOB_EVIDENCE.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
