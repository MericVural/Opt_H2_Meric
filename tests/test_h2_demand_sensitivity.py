"""Demand-volume interventions, independent provenance and LP scale checks.

The calendar checks use all 8,784 real 2024 hours. Solver tests use a declared
24-hour synthetic period only, and establish software behavior rather than
empirical annual results. No historical exports are changed or solved here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from config_h2 import Scenario, iter_scalar_parameters
from eu_demand_profiles import demand_profile
from eu_site_configuration import DEFAULT_EU_DESIGN_PATH, EU_SITE_IDS, load_eu_site_configuration
from h2_input_data import validate_hourly_input
from h2_sensitivity_overrides import apply_sensitivity_override
import run_h2_sensitivity as sensitivity
import run_single_site_h2 as single
from validate_h2_results import validate_h2_results

BASE_ANNUAL_KG = 3_650_000.0
FACTORS = (0.5, 0.75, 1.0, 1.25, 1.5)
TOTALS = (1_825_000.0, 2_737_500.0, 3_650_000.0, 4_562_500.0, 5_475_000.0)
SCENARIOS = (Scenario.REFERENCE, Scenario.RED_MONTHLY, Scenario.RED_HOURLY)
PROFILES = ("D0", "D1", "D2")
PARAMETER = "h2_demand_multiplier"
SOURCE = "Synthetic software test of the user-prescribed demand factors"
NOTE = "Unchanged normalized delivery profile; not empirical annual evidence"
OPERATION = "multiply_hourly_h2_demand_preserve_profile"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, contents: dict) -> None:
    path.write_text(json.dumps(contents, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def override(factor: float) -> dict:
    return {"parameter": PARAMETER, "value": factor, "source": SOURCE, "note": NOTE}


def calendar_axis(zone: str) -> pd.DatetimeIndex:
    start = pd.Timestamp("2024-01-01", tz=zone).tz_convert("UTC")
    end = pd.Timestamp("2025-01-01", tz=zone).tz_convert("UTC")
    return pd.date_range(start, end, freq="h", inclusive="left")


def full_frame(selected, profile: str) -> tuple[pd.DataFrame, dict]:
    axis = calendar_axis(selected.calendar_timezone)
    demand, profile_receipt = demand_profile(axis, profile=profile,
        timezone=selected.calendar_timezone, historical_year=2024)
    # Exogenous columns intentionally vary, and arbitrary text includes values
    # that pandas would otherwise coerce. Equality covers more than one scalar.
    hours = np.arange(len(axis))
    frame = pd.DataFrame({"timestamp": axis,
        "pv_capacity_factor": np.maximum(0, np.sin((hours % 24 - 6) * np.pi / 12)),
        "wind_capacity_factor": .3 + .15 * np.sin(hours * np.pi / 17),
        "electricity_price": 75 + 25 * np.cos(hours * np.pi / 12),
        "grid_emission_factor": 300 + hours % 31,
        "regulatory_grid_emission_factor": np.full(len(axis), 60.),
        "h2_demand": demand.to_numpy(),
        "arbitrary_text": np.resize(["NA", "001", "", "a,b", "ümlaut", "2e3"], len(axis))})
    return frame, profile_receipt


def input_contract(path: Path, selected, profile_receipt: dict, *, full_calendar: bool) -> dict:
    contents = {"schema_version": "1.0", "input_sha256": digest(path),
        "emission_factor_mode": "explicit_separate_factors",
        "site_id": selected.metadata["site_id"], "country_code": selected.site.country_code,
        "calendar_timezone": selected.calendar_timezone, "historical_year": 2024,
        "price_year": 2023, "annualization_basis": "historical_calendar_year",
        "annual_hours": 8784, "demand_profile": profile_receipt,
        "emission_factor_sources": {role: {
            "source_description": "Synthetic separate factor; no empirical claim",
            "reference_year": 2024, "spatial_scope": "synthetic_test_system",
            "unit": "kg_CO2e/MWh", "emissions_basis": "synthetic_" + role,
        } for role in ("operational", "regulatory")}}
    # expected_hours is omitted for the explicit short synthetic period.
    if full_calendar:
        contents["expected_hours"] = 8784
    return contents


def write_cases(path: Path, *, factors=(.5, .75, 1.25, 1.5)) -> None:
    rows = [{"case_id": "baseline", "parameter": "baseline", "level": "base",
        "label": "100% synthetic baseline", "value": "", "unit": "-", "source": SOURCE, "note": NOTE}]
    rows.extend({"case_id": "demand_" + str(round(f * 100)), "parameter": PARAMETER,
        "level": "test", "label": f"{f * 100:g}% demand", "value": f,
        "unit": "factor", "source": SOURCE, "note": NOTE} for f in factors)
    pd.DataFrame(rows).to_csv(path, index=False)


@pytest.mark.parametrize("site_id", EU_SITE_IDS)
@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("factor,total", tuple(zip(FACTORS, TOTALS)))
def test_full_2024_volume_profile_mask_and_exogenous_columns(site_id, profile, factor, total):
    selected = load_eu_site_configuration(site_id)
    frame, profile_receipt = full_frame(selected, profile)
    frame.attrs.update(emission_factor_mode="explicit_separate_factors",
        emission_factor_sources={role: {"source_description": "Synthetic", "reference_year": 2024,
            "spatial_scope": "synthetic", "unit": "kg_CO2e/MWh", "emissions_basis": role}
            for role in ("operational", "regulatory")})
    parent = validate_hourly_input(frame, require_separate_emission_factors=True)
    snapshot = parent.copy(deep=True)
    case = sensitivity.SensitivityCase("scaled", PARAMETER, "test", "Scaled demand",
        factor, "factor", SOURCE, NOTE)
    config, child = sensitivity._apply_case(case, selected.config, parent)
    np.testing.assert_allclose(child.h2_demand, parent.h2_demand * factor, rtol=1e-12, atol=1e-12)
    assert child.h2_demand.sum() == pytest.approx(total, abs=1e-6)
    assert (child.h2_demand > 0).equals(parent.h2_demand > 0)
    assert (child.h2_demand > 0).sum() == {"D0": 8784, "D1": 4392, "D2": 3144}[profile]
    assert len(child) == 8784 and child.timestamp.equals(parent.timestamp)
    pd.testing.assert_frame_equal(child.drop(columns="h2_demand"), parent.drop(columns="h2_demand"))
    pd.testing.assert_frame_equal(parent, snapshot)
    assert config.study.h2_demand_kg_per_day.value == pytest.approx(total / 366)
    assert config.study.h2_demand_kg_per_year == pytest.approx(total)
    assert config.study.annual_hours.value == 8784
    before = dict(iter_scalar_parameters(selected.config))
    after = dict(iter_scalar_parameters(config))
    for name in before:
        if name != "study.h2_demand_kg_per_day":
            assert after[name] == before[name], name
    assert profile_receipt["annual_kg"] == BASE_ANNUAL_KG


@pytest.mark.parametrize("value", [0., -1., np.nan, np.inf, -np.inf, True, False, "1.25", None])
def test_demand_multiplier_rejects_invalid_values(value):
    selected = load_eu_site_configuration(EU_SITE_IDS[0])
    with pytest.raises((ValueError, TypeError)):
        apply_sensitivity_override(selected.config, override(value))


@pytest.fixture(scope="module", params=[(site, profile) for site in EU_SITE_IDS for profile in PROFILES])
def demand_results(tmp_path_factory, request):
    site_id, profile = request.param
    root = tmp_path_factory.mktemp(site_id + "_" + profile)
    source_dir = root / "source"
    source_dir.mkdir()
    design = source_dir / "immutable_design.json"
    design.write_bytes(DEFAULT_EU_DESIGN_PATH.read_bytes())
    selected = load_eu_site_configuration(site_id, design_path=design)
    full, profile_receipt = full_frame(selected, profile)
    local = pd.to_datetime(full.timestamp).dt.tz_convert(selected.calendar_timezone)
    period = full.loc[(local.dt.month == 1) & (local.dt.day == 2)].copy()
    assert len(period) == 24 and period.h2_demand.sum() > 0
    source, contract, cases = source_dir / "input.csv", source_dir / "input.metadata.json", source_dir / "cases.csv"
    period.to_csv(source, index=False)
    write_json(contract, input_contract(source, selected, profile_receipt, full_calendar=False))
    write_cases(cases)
    artifacts = sensitivity.run_h2_sensitivity(source, cases, root / "results", scenarios=SCENARIOS,
        solver_backend="scipy-highs", emission_factor_metadata_path=contract,
        require_separate_emission_factors=True, eu_site=site_id, eu_design_path=design)
    comparison = pd.read_csv(artifacts.comparison_path)
    for case_id, group in comparison.groupby("case_id", sort=False):
        group = group.copy()
        group["scenario_id"] = group.scenario.map({"reference": "S0", "red_monthly": "S1", "red_hourly": "S2"})
        group["result_directory"] = group.scenario
        directory = artifacts.output_directory / "runs" / case_id
        group.to_csv(directory / "scenario_comparison.csv", index=False)
        validation = validate_h2_results(directory, expected_hours=24)
        if not validation.all_checks_passed:
            checks = pd.read_csv(validation.checks_path)
            pytest.fail("Independent native validation failed:\n" + checks.loc[~checks.passed].to_string(index=False))
    return dict(root=root, source=source, contract=contract, cases=cases, design=design,
        selected=selected, profile=profile, artifacts=artifacts, comparison=comparison,
        profile_receipt=profile_receipt)


def test_real_highs_three_scenario_volume_homogeneity_and_source_contract(demand_results):
    fixture = demand_results
    artifacts, comparison = fixture["artifacts"], fixture["comparison"]
    assert len(comparison) == 15
    assert comparison.solver_status.eq("optimal").all()
    parent = pd.read_csv(fixture["source"], dtype=str, keep_default_na=False)
    source_contract = json.loads(fixture["contract"].read_text(encoding="utf-8"))
    for factor in FACTORS:
        case_id = "baseline" if factor == 1 else "demand_" + str(round(factor * 100))
        child_path = artifacts.output_directory / "case_inputs" / f"{case_id}.csv"
        child = pd.read_csv(child_path, dtype=str, keep_default_na=False)
        receipt = json.loads(child_path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
        assert receipt["input_sha256"] == digest(child_path)
        assert receipt["parent_input"]["sha256"] == digest(fixture["source"])
        assert receipt["parent_input"]["metadata_sha256"] == digest(fixture["contract"])
        assert receipt["emission_factor_sources"] == source_contract["emission_factor_sources"]
        expected_profile = deepcopy(fixture["profile_receipt"])
        for key in ("annual_kg", "kg_per_active_hour"):
            expected_profile[key] *= factor
        assert receipt["demand_profile"] == expected_profile
        assert child.arbitrary_text.equals(parent.arbitrary_text)
        for column in parent.columns:
            if column == "h2_demand":
                np.testing.assert_allclose(pd.to_numeric(child[column]), pd.to_numeric(parent[column]) * factor,
                    rtol=1e-12, atol=1e-12)
            elif column == "timestamp":
                assert pd.to_datetime(child[column], utc=True).equals(pd.to_datetime(parent[column], utc=True))
            elif column != "arbitrary_text":
                np.testing.assert_allclose(pd.to_numeric(child[column]), pd.to_numeric(parent[column]), rtol=0., atol=1e-12)
            else:
                assert child[column].equals(parent[column]), column
        for scenario in SCENARIOS:
            baseline = artifacts.runs[("baseline", scenario.value)]
            run = artifacts.runs[(case_id, scenario.value)]
            assert run.result.objective_eur_per_year == pytest.approx(baseline.result.objective_eur_per_year * factor,
                rel=2e-7, abs=1e-3)
            assert run.result.lcoh_eur_per_kg_h2 == pytest.approx(baseline.result.lcoh_eur_per_kg_h2,
                rel=2e-7, abs=1e-7)
            assert run.result.annual_h2_delivered_kg == pytest.approx(baseline.result.annual_h2_delivered_kg * factor)
            metadata = json.loads(run.metadata_path.read_text(encoding="utf-8"))
            assert metadata["model_parameters"]["study.h2_demand_kg_per_day"]["value"] == pytest.approx(BASE_ANNUAL_KG * factor / 366)
            assert metadata["calendar_scope"]["annualization"]["annual_hours"] == 8784
            assert metadata["calendar_scope"]["annualization"]["factor"] == 366
            effective = metadata["input"]["eu_site_configuration"]
            assert effective["design_sha256"] == digest(fixture["design"])
            assert effective["annualization"]["annual_h2_delivery_kg"] == pytest.approx(BASE_ANNUAL_KG * factor)
            if factor != 1:
                assert effective["annualization"]["baseline_annual_h2_delivery_kg"] == BASE_ANNUAL_KG
                assert effective["annualization"]["demand_multiplier"] == factor
                assert effective["annualization"]["effective_delivery_is_sensitivity_assumption"] is True
                assert metadata["sensitivity_override"]["operation"] == OPERATION


def test_scaled_optimal_baseline_is_independently_feasible(demand_results):
    fixture = demand_results
    config = fixture["selected"].config
    source = pd.read_csv(fixture["source"])
    specific_pem = config.technologies.electrolyzer.specific_electricity_kwh_per_kg_h2.value / 1000
    compressor = config.technologies.compressor
    specific_compressor = compressor.isentropic_energy_kwh_per_kg_h2.value / (
        compressor.isentropic_efficiency_fraction.value * compressor.mechanical_efficiency_fraction.value * 1000)
    survival = 1 - compressor.h2_loss_fraction.value
    for scenario in SCENARIOS:
        base = fixture["artifacts"].runs[("baseline", scenario.value)].result
        for factor in FACTORS:
            capacity = {key: value * factor for key, value in base.capacities.items()}
            hourly = base.hourly_operation.copy()
            quantity_columns = [column for column in hourly.columns if column.endswith("_mwh") or column.endswith("_kg")]
            hourly[quantity_columns] *= factor
            assert hourly[quantity_columns].min().min() >= -1e-7
            np.testing.assert_allclose(hourly.h2_demand_kg, source.h2_demand * factor, atol=1e-7)
            np.testing.assert_allclose(hourly.pv_self_consumption_mwh + hourly.wind_self_consumption_mwh + hourly.grid_import_mwh,
                hourly.electrolyzer_electricity_mwh + hourly.compressor_electricity_mwh, atol=1e-7)
            np.testing.assert_allclose(hourly.h2_production_kg, hourly.electrolyzer_electricity_mwh / specific_pem, atol=1e-5)
            np.testing.assert_allclose(hourly.compressor_electricity_mwh, hourly.h2_production_kg * specific_compressor, atol=1e-7)
            np.testing.assert_allclose(hourly.h2_storage_level_kg - np.roll(hourly.h2_storage_level_kg.to_numpy(), 1),
                hourly.h2_production_kg * survival - hourly.h2_demand_kg, atol=1e-5)
            assert (hourly.h2_storage_level_kg <= capacity["h2_storage_capacity_kg"] + 1e-5).all()
            assert (hourly.electrolyzer_electricity_mwh <= capacity["electrolyzer_capacity_mw"] + 1e-7).all()
            assert (hourly.compressor_electricity_mwh <= capacity["compressor_capacity_mw"] + 1e-7).all()
            assert (hourly.pv_generation_mwh <= capacity["pv_capacity_mw"] * source.pv_capacity_factor + 1e-7).all()
            assert (hourly.wind_generation_mwh <= capacity["wind_capacity_mw"] * source.wind_capacity_factor + 1e-7).all()
            renewable = hourly.pv_generation_mwh + hourly.wind_generation_mwh
            consumption = hourly.electrolyzer_electricity_mwh + hourly.compressor_electricity_mwh
            if scenario is Scenario.RED_MONTHLY:
                assert renewable.sum() >= consumption.sum() - 1e-7
            elif scenario is Scenario.RED_HOURLY:
                assert (renewable >= consumption - 1e-7).all()
            assert sum(value * factor for value in base.annual_costs.values()) == pytest.approx(base.objective_eur_per_year * factor, rel=1e-10)


@pytest.mark.parametrize("tampering", ["demand_hour", "price", "factor", "parent_hash", "snapshot_hash", "annual_target", "profile_name", "active_hours"])
def test_tampered_demand_contract_is_rejected_before_solver(demand_results, tmp_path, monkeypatch, tampering):
    fixture = demand_results
    original = fixture["artifacts"].output_directory / "case_inputs" / "demand_125.csv"
    child, sidecar = tmp_path / "input.csv", tmp_path / "input.metadata.json"
    shutil.copyfile(original, child)
    contract = json.loads(original.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    if tampering in ("demand_hour", "price"):
        data = pd.read_csv(child, dtype=str, keep_default_na=False)
        column = "h2_demand" if tampering == "demand_hour" else "electricity_price"
        row = int(np.flatnonzero(pd.to_numeric(data.h2_demand).to_numpy() > 0)[0])
        data.loc[row, column] = str(float(data.loc[row, column]) + 1)
        data.to_csv(child, index=False)
        contract["input_sha256"] = digest(child)
    elif tampering == "factor":
        contract["case_transformation"]["value"] = 1.5
    elif tampering == "parent_hash":
        contract["parent_input"]["sha256"] = "0" * 64
    elif tampering == "snapshot_hash":
        contract["baseline_configuration"]["sha256"] = "0" * 64
    elif tampering == "annual_target":
        contract["demand_profile"]["annual_kg"] += 1
    elif tampering == "profile_name":
        contract["demand_profile"]["profile"] = "D2" if fixture["profile"] != "D2" else "D1"
    else:
        contract["demand_profile"]["active_delivery_hours"] += 1
    write_json(sidecar, contract)
    def forbidden(*args, **kwargs):
        pytest.fail("A tampered demand contract must fail before the solver")
    monkeypatch.setattr(single, "optimize_hydrogen_system", forbidden)
    with pytest.raises((ValueError, single.H2RunError)):
        single.run_single_site_h2(child, tmp_path / "forbidden", solver_backend="scipy-highs",
            emission_factor_metadata_path=sidecar, require_separate_emission_factors=True,
            eu_site=fixture["selected"].metadata["site_id"], eu_design_path=fixture["design"],
            sensitivity_override=override(1.25))
    assert not (tmp_path / "forbidden").exists()


@pytest.mark.parametrize("tampering", ["365_day_scalar", "effective_annual_target", "multiplier_receipt", "undeclared_cost", "missing_intervention", "demand_hour", "profile_receipt"])
def test_independent_validator_rejects_demand_export_tampering(demand_results, tmp_path, tampering):
    fixture = demand_results
    original = fixture["artifacts"].output_directory / "runs" / "demand_125"
    copied = tmp_path / "group"
    shutil.copytree(original, copied)
    path = copied / "reference" / "run_metadata.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if tampering == "365_day_scalar":
        metadata["model_parameters"]["study.h2_demand_kg_per_day"]["value"] = BASE_ANNUAL_KG * 1.25 / 365
    elif tampering == "effective_annual_target":
        metadata["input"]["eu_site_configuration"]["annualization"]["annual_h2_delivery_kg"] += 1
    elif tampering == "multiplier_receipt":
        metadata["input"]["eu_site_configuration"]["annualization"]["demand_multiplier"] = 1.5
    elif tampering == "undeclared_cost":
        metadata["model_parameters"]["technologies.pv.capex_eur_per_kw"]["value"] *= 2
    elif tampering == "missing_intervention":
        del metadata["sensitivity_override"]
        del metadata["input"]["sensitivity_provenance"]
    elif tampering == "profile_receipt":
        metadata["input"]["declared_input_context"]["demand_profile"]["annual_kg"] += 1
    else:
        exported = copied / "reference" / "validated_input.csv"
        data = pd.read_csv(exported)
        row = int(np.flatnonzero(data.h2_demand.to_numpy() > 0)[0])
        data.loc[row, "h2_demand"] += 1
        data.to_csv(exported, index=False)
    write_json(path, metadata)
    checked = validate_h2_results(copied, expected_hours=24, output_directory=tmp_path / "validation")
    assert not checked.all_checks_passed
    checks = pd.read_csv(checked.checks_path)
    failed = set(checks.loc[~checks.passed, "check_id"])
    expected = ("annualization_source_contract" if tampering in ("effective_annual_target", "multiplier_receipt")
        else "sensitivity_parent_input_contract" if tampering in ("demand_hour", "profile_receipt")
        else "sensitivity_one_factor_configuration")
    assert expected in failed, failed
