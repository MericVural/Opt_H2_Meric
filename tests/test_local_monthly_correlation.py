"""Explicit calendar tests and small actual boundary solves, never annual solves."""
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from config_h2 import DEFAULT_CONFIG, Scenario
import eu_site_configuration as eu
from eu_test_designs import write_calendar_design
from opt_hydrogen_functions import optimize_hydrogen_system, _add_regulatory_emission_columns
from red_iii_data import build_correlation_periods, assess_red_iii_compliance, EligibilityEvidence
from run_h2_scenarios import run_h2_scenarios
from validate_h2_results import validate_h2_results, _check_temporal_calendar_contract


@pytest.mark.parametrize("zone", ["Europe/Berlin", "Europe/Madrid"])
def test_full_local_leap_year_has_twelve_months_and_no_neighbor_year(zone):
    timestamps = pd.Series(pd.date_range("2023-12-31T23:00:00Z", periods=8784, freq="h"))
    labels = build_correlation_periods(timestamps, "monthly", calendar_timezone=zone)
    assert labels.iloc[0] == "2024-01"
    assert labels.iloc[-1] == "2024-12"
    assert labels.drop_duplicates().tolist() == [f"2024-{month:02}" for month in range(1, 13)]
    assert labels.value_counts()["2024-03"] == 743  # Spring change loses one local-clock label.
    assert labels.value_counts()["2024-10"] == 745  # Autumn has two distinct physical 02:00 hours.
    assert build_correlation_periods(timestamps, "monthly").iloc[0] == "2023-12"


@pytest.mark.parametrize("zone", ["Europe/Berlin", "Europe/Madrid"])
def test_s2_fall_clock_change_preserves_two_distinct_physical_hours(zone):
    timestamps = pd.Series(pd.date_range("2024-10-27T00:00:00Z", periods=2, freq="h"))
    assert timestamps.dt.tz_convert(zone).dt.hour.tolist() == [2, 2]
    labels = build_correlation_periods(timestamps, "hourly", calendar_timezone=zone)
    assert labels.tolist() == ["2024-10-27T00:00Z", "2024-10-27T01:00Z"]
    operation = pd.DataFrame({"timestamp": timestamps, "rf_nbo_electricity_mwh": [0., 1.],
                              "eligible_renewable_electricity_mwh": [1., 0.]})
    check = assess_red_iii_compliance(operation, temporal_mode="hourly", calendar_timezone=zone,
        evidence=EligibilityEvidence(True, True, True), product_intensity_kg_co2e_per_kg_h2=0.)
    assert not check.temporal_compliant
    assert len(check.period_results) == 2


@pytest.mark.parametrize("zone", ["Unknown/Timezone", "", None])
def test_invalid_calendar_is_rejected_in_configuration_and_independent_red_assessment(zone):
    with pytest.raises(ValueError, match="IANA"):
        replace(DEFAULT_CONFIG.study, temporal_correlation_timezone=zone).validate()
    with pytest.raises(ValueError, match="IANA"):
        build_correlation_periods(pd.Series(["2024-01-01T00:00Z"]), "monthly", calendar_timezone=zone)


def boundary_frame():
    solar = np.zeros(24)
    solar[[0, 11, 12]] = 1.
    return pd.DataFrame({"timestamp": pd.date_range("2024-02-29T12:00Z", periods=24, freq="h"),
        "pv_capacity_factor": solar, "wind_capacity_factor": np.zeros(24),
        "electricity_price": np.zeros(24), "grid_emission_factor": np.full(24, 300.),
        "h2_demand": np.full(24, 100.)})


def synthetic_monthly_config(zone):
    # Artificial test penalty isolates monthly constraints from storage arbitrage.
    storage = replace(DEFAULT_CONFIG.technologies.h2_storage,
        capex_eur_per_kg_h2=replace(DEFAULT_CONFIG.technologies.h2_storage.capex_eur_per_kg_h2,
                                  value=1_000_000., source="Synthetic calendar-isolation test"))
    return replace(DEFAULT_CONFIG, scenario=Scenario.RED_MONTHLY,
        study=replace(DEFAULT_CONFIG.study, temporal_correlation_timezone=zone),
        technologies=replace(DEFAULT_CONFIG.technologies, h2_storage=storage))


@pytest.fixture(scope="module")
def actual_boundary_results():
    return {(backend, zone): optimize_hydrogen_system(boundary_frame(),
            config=synthetic_monthly_config(zone), solver_backend=backend)
            for backend in ("gurobi", "scipy_highs") for zone in ("UTC", "Europe/Berlin")}


@pytest.mark.parametrize("backend", ["gurobi", "scipy_highs"])
def test_local_month_boundary_changes_actual_s1_capacity_and_cost(actual_boundary_results, backend):
    utc = actual_boundary_results[(backend, "UTC")]
    local = actual_boundary_results[(backend, "Europe/Berlin")]
    for result in (utc, local):
        assert result.capacities["h2_storage_capacity_kg"] == pytest.approx(0., abs=1e-6)
        assert result.red_iii_temporal_compliant
        assert result.red_iii_correlation_periods == 2
        assert result.hourly_operation.compressor_electricity_mwh.sum() > 0
        assert result.hourly_operation.rf_nbo_electricity_mwh.to_numpy() == pytest.approx(
            (result.hourly_operation.electrolyzer_electricity_mwh
             + result.hourly_operation.compressor_electricity_mwh).to_numpy())
    assert local.capacities["pv_capacity_mw"] == pytest.approx(utc.capacities["pv_capacity_mw"] * 11 / 12, rel=1e-7)
    assert local.objective_eur_per_year < utc.objective_eur_per_year
    utc_operation = utc.hourly_operation
    local_keys = pd.to_datetime(utc_operation.timestamp, utc=True).dt.tz_convert("Europe/Berlin").dt.strftime("%Y-%m")
    assert local_keys.value_counts().to_dict() == {"2024-03": 13, "2024-02": 11}


def test_both_solver_paths_agree_on_each_boundary_calendar(actual_boundary_results):
    for zone in ("UTC", "Europe/Berlin"):
        gurobi, highs = (actual_boundary_results[(backend, zone)] for backend in ("gurobi", "scipy_highs"))
        assert gurobi.objective_eur_per_year == pytest.approx(highs.objective_eur_per_year, rel=1e-8)
        assert gurobi.capacities == pytest.approx(highs.capacities, rel=1e-7, abs=1e-6)
        assert gurobi.annual_regulatory_emissions_kg_co2e == pytest.approx(0., abs=1e-6)


def test_regulatory_deficit_and_ex_post_assessment_share_the_local_month():
    operation = pd.DataFrame({"timestamp": ["2024-02-29T23:00Z", "2024-03-01T00:00Z"],
        "grid_import_mwh": [0., 2.], "regulatory_grid_emission_factor_kg_co2e_per_mwh": [100., 100.],
        "rf_nbo_electricity_mwh": [0., 2.], "eligible_renewable_electricity_mwh": [2., 0.]})
    operation.attrs["emissions_reporting"] = "regulatory_only"
    utc = _add_regulatory_emission_columns(operation, Scenario.RED_MONTHLY)
    operation.attrs["temporal_correlation_timezone"] = "Europe/Berlin"
    local = _add_regulatory_emission_columns(operation, Scenario.RED_MONTHLY)
    assert utc.regulatory_non_renewable_electricity_mwh.sum() == pytest.approx(2.)
    assert local.regulatory_non_renewable_electricity_mwh.sum() == pytest.approx(0.)
    for zone, expected in [("UTC", False), ("Europe/Berlin", True)]:
        check = assess_red_iii_compliance(operation, temporal_mode="monthly", calendar_timezone=zone,
            evidence=EligibilityEvidence(True, True, True), product_intensity_kg_co2e_per_kg_h2=0.)
        assert check.temporal_compliant is expected


def export_local_batch(tmp_path):
    design_path = write_calendar_design(eu.DEFAULT_EU_DESIGN_PATH, tmp_path / "design.json", 2024)
    source = tmp_path / "input.csv"
    hourly = boundary_frame()
    hourly["pv_capacity_factor"] = 1.
    hourly.to_csv(source, index=False)
    return run_h2_scenarios(source, tmp_path / "results", solver_backend="scipy-highs",
        eu_site="hamburg_moorburg", eu_design_path=design_path)


def test_export_and_independent_validator_document_the_local_month_basis(tmp_path):
    exported = export_local_batch(tmp_path)
    checked = validate_h2_results(exported.output_directory, expected_hours=24)
    assert checked.all_checks_passed
    batch = json.loads((exported.output_directory / "scenario_comparison_metadata.json").read_text(encoding="utf-8"))
    assert batch["temporal_calendar"] == {"timezone": "Europe/Berlin",
        "monthly_grouping_basis": "site_local_calendar_month", "hourly_grouping_basis": "physical_utc_hour"}
    for scenario_run in exported.scenario_runs.values():
        metadata = json.loads(scenario_run.metadata_path.read_text(encoding="utf-8"))
        assert metadata["model_calendar"]["temporal_correlation_timezone"] == "Europe/Berlin"
        assert metadata["calendar_scope"]["monthly_correlation_calendar"] == "Europe/Berlin"
        assert metadata["result"]["red_iii_temporal_check"]["calendar_timezone"] == "Europe/Berlin"


@pytest.mark.parametrize("mutation", ["scope_timezone", "model_timezone", "monthly_basis", "red_check_timezone", "missing_configuration", "source_design", "batch_timezone", "coordinated_output_timezone"])
def test_independent_validator_detects_tampered_calendar(tmp_path, mutation):
    exported = export_local_batch(tmp_path)
    run = exported.scenario_runs["S1"]
    metadata = json.loads(run.metadata_path.read_text(encoding="utf-8"))
    if mutation == "scope_timezone": metadata["calendar_scope"]["monthly_correlation_calendar"] = "UTC"
    elif mutation == "model_timezone": metadata["model_calendar"]["temporal_correlation_timezone"] = "UTC"
    elif mutation == "monthly_basis": metadata["calendar_scope"]["monthly_grouping_basis"] = "utc_calendar_month"
    elif mutation == "red_check_timezone": metadata["result"]["red_iii_temporal_check"]["calendar_timezone"] = "UTC"
    elif mutation == "missing_configuration": del metadata["model_calendar"]
    elif mutation == "source_design":
        path = Path(metadata["input"]["eu_site_configuration"]["design_path"])
        design = json.loads(path.read_text(encoding="utf-8"))
        design["time"]["monthly_grouping"] = "UTC"
        path.write_text(json.dumps(design), encoding="utf-8")
    elif mutation == "batch_timezone":
        path = exported.output_directory / "scenario_comparison_metadata.json"
        batch = json.loads(path.read_text(encoding="utf-8"))
        batch["temporal_calendar"]["timezone"] = "UTC"
        path.write_text(json.dumps(batch), encoding="utf-8")
    elif mutation == "coordinated_output_timezone":
        metadata["model_calendar"]["temporal_correlation_timezone"] = "UTC"
        metadata["calendar_scope"].update(monthly_correlation_calendar="UTC", monthly_grouping_basis="utc_calendar_month",
            site_timezone_applied_to_monthly_correlation=False)
        metadata["result"]["red_iii_temporal_check"]["calendar_timezone"] = "UTC"
    run.metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    checked = validate_h2_results(exported.output_directory, expected_hours=24)
    assert not checked.all_checks_passed
    checks = pd.read_csv(checked.checks_path)
    failed = checks[~checks.passed]
    assert failed.check_id.str.startswith("temporal_calendar_").any()


def test_older_recorded_eu_archive_keeps_utc_calendar_without_inference():
    metadata = {"schema_version": "1.5", "input": {"eu_site_configuration": {"calendar_timezone": "Europe/Berlin"}},
        "calendar_scope": {"requested_site_timezone": "Europe/Berlin", "monthly_correlation_calendar": "UTC",
                           "site_timezone_applied_to_monthly_correlation": False}}
    checks = []
    assert _check_temporal_calendar_contract(checks, "red_monthly", metadata, None) == "UTC"
    assert all(check["passed"] for check in checks)


@pytest.mark.parametrize("location", ["summary", "metadata"])
def test_independent_validator_detects_invented_correlation_period_count(tmp_path, location):
    exported = export_local_batch(tmp_path)
    run = exported.scenario_runs["S1"]
    if location == "summary":
        summary = pd.read_csv(run.summary_path)
        summary["red_iii_correlation_periods"] = 13
        summary.to_csv(run.summary_path, index=False)
    else:
        metadata = json.loads(run.metadata_path.read_text(encoding="utf-8"))
        metadata["result"]["red_iii_temporal_check"]["number_of_correlation_periods"] = 13
        run.metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    checked = validate_h2_results(exported.output_directory, expected_hours=24)
    assert not checked.all_checks_passed
    checks = pd.read_csv(checked.checks_path)
    assert not checks.loc[(checks.scenario == "red_monthly") & (checks.check_id == "red_temporal_period_count"), "passed"].all()
