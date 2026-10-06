"""Regulatory-only exports must represent missing operational data honestly.

All source descriptions and hourly data in this file are synthetic fixtures.
They test software contracts and do not establish scientific factor suitability.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from h2_input_data import HourlyInputError, validate_hourly_input
from opt_hydrogen_functions import optimize_hydrogen_system
from run_h2_scenarios import main as scenarios_main, run_h2_scenarios
from run_single_site_h2 import H2RunError, main as single_main, run_single_site_h2
from validate_h2_results import validate_h2_results


OPERATIONAL_SUMMARY_COLUMNS = (
    "annual_grid_emissions_kg_co2e",
    "operational_emission_intensity_kg_co2e_per_kg_h2",
)
OPERATIONAL_HOURLY_COLUMNS = (
    "grid_emission_factor_kg_co2e_per_mwh",
    "operational_grid_emissions_kg_co2e",
)


def _regulatory_source() -> dict[str, object]:
    return {
        "source_description": "Synthetic regulatory fixture; no empirical factor",
        "reference_year": 2025,
        "spatial_scope": "synthetic_test_system",
        "unit": "kg_CO2e/MWh",
        "emissions_basis": "synthetic_regulatory_CO2e",
    }


def _case(*, complete: bool = False, pv: float = 0.0) -> pd.DataFrame:
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=24, freq="h", tz="UTC"),
        "pv_capacity_factor": np.full(24, pv),
        "wind_capacity_factor": np.zeros(24),
        "electricity_price": np.zeros(24),
        "h2_demand": np.full(24, 100.0),
        "regulatory_grid_emission_factor": np.linspace(50.0, 96.0, 24),
    })
    sources = {"regulatory": _regulatory_source()}
    if complete:
        frame["grid_emission_factor"] = np.linspace(250.0, 480.0, 24)
        sources["operational"] = {
            **_regulatory_source(),
            "source_description": "Synthetic operational fixture; no empirical factor",
            "emissions_basis": "synthetic_direct_CO2e",
        }
    frame.attrs["emission_factor_mode"] = (
        "explicit_separate_factors" if complete else "regulatory_only"
    )
    frame.attrs["emission_factor_sources"] = sources
    return frame


def _write_contract(directory: Path, frame: pd.DataFrame) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    input_path = directory / "input.csv"
    contract_path = directory / "factor_metadata.json"
    frame.to_csv(input_path, index=False)
    contract_path.write_text(json.dumps({
        "schema_version": "1.0",
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "emission_factor_mode": frame.attrs["emission_factor_mode"],
        "emission_factor_sources": frame.attrs["emission_factor_sources"],
    }), encoding="utf-8")
    return input_path, contract_path


def _assert_absent_operational_exports(directory: Path) -> None:
    summary = pd.read_csv(directory / "summary.csv")
    operation = pd.read_csv(directory / "hourly_operation.csv")
    validated = pd.read_csv(directory / "validated_input.csv")
    metadata = json.loads((directory / "run_metadata.json").read_text(encoding="utf-8"))
    assert summary.loc[0, "emissions_reporting"] == "regulatory_only"
    assert summary.loc[0, "operational_emissions_status"] == "not_evaluated"
    assert summary.loc[0, "emission_factor_mode"] == "regulatory_only"
    assert summary.loc[0, list(OPERATIONAL_SUMMARY_COLUMNS)].isna().all()
    assert "grid_emission_factor" not in validated.columns
    assert "regulatory_grid_emission_factor" in validated.columns
    assert not set(OPERATIONAL_HOURLY_COLUMNS).intersection(operation.columns)
    assert metadata["input"]["emissions_reporting"] == "regulatory_only"
    assert metadata["input"]["emission_factor_mode"] == "regulatory_only"
    assert metadata["input"]["emission_factor_sources"] == {"regulatory": _regulatory_source()}
    assert metadata["result"]["emissions_reporting"] == "regulatory_only"
    assert metadata["result"]["operational_emissions_status"] == "not_evaluated"
    emissions = metadata["result"]["emissions"]
    assert emissions["operational_grid_emissions_kg_co2e_per_year"] is None
    assert emissions["operational_intensity_kg_co2e_per_kg_h2"] is None
    assert np.isfinite(summary.loc[0, "annual_regulatory_emissions_kg_co2e"])
    assert np.isfinite(operation["regulatory_grid_emission_factor_kg_co2e_per_mwh"]).all()


def _export_scenarios(directory: Path) -> Path:
    input_path, contract_path = _write_contract(directory / "source", _case(pv=1.0))
    root = directory / "scenarios"
    artifacts = run_h2_scenarios(
        input_path, root, solver_backend="scipy-highs",
        emission_factor_metadata_path=contract_path,
        emissions_reporting="regulatory_only",
    )
    batch_metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert batch_metadata["input"]["emission_factor_mode"] == "regulatory_only"
    assert batch_metadata["input"]["emission_factor_sources"] == {"regulatory": _regulatory_source()}
    for subdirectory in ("S0_reference", "S1_red_monthly", "S2_red_hourly"):
        _assert_absent_operational_exports(root / subdirectory)
    return root


def test_regulatory_only_input_preserves_sources_without_inventing_operational_values() -> None:
    frame = _case()
    validated = validate_hourly_input(frame, expected_hours=24, emissions_reporting="regulatory_only")
    assert "grid_emission_factor" not in validated.columns
    assert "grid_emission_factor" not in validated.attrs["column_units"]
    assert validated.attrs["emission_factor_mode"] == "regulatory_only"
    assert validated.attrs["emission_factor_sources"] == {"regulatory": _regulatory_source()}
    assert validated.attrs["column_units"]["regulatory_grid_emission_factor"] == "kg_CO2e/MWh"
    validated.attrs["emission_factor_sources"]["regulatory"]["source_description"] = "Changed"
    assert frame.attrs["emission_factor_sources"]["regulatory"] == _regulatory_source()


def test_default_complete_mode_requires_operational_data() -> None:
    with pytest.raises(HourlyInputError):
        validate_hourly_input(_case())


def test_regulatory_only_rejects_the_contradictory_separate_factor_requirement() -> None:
    with pytest.raises(HourlyInputError):
        validate_hourly_input(_case(), emissions_reporting="regulatory_only", require_separate_emission_factors=True)


def test_regulatory_only_rejects_an_operational_placeholder() -> None:
    frame = _case()
    frame["grid_emission_factor"] = 0.0
    with pytest.raises(HourlyInputError):
        validate_hourly_input(frame, emissions_reporting="regulatory_only")


def test_regulatory_only_rejects_an_undocumented_regulatory_factor() -> None:
    frame = _case()
    frame.attrs.clear()
    with pytest.raises(HourlyInputError):
        validate_hourly_input(frame, emissions_reporting="regulatory_only")


def test_regulatory_only_still_requires_a_regulatory_factor_column() -> None:
    frame = _case().drop(columns="regulatory_grid_emission_factor")
    with pytest.raises(HourlyInputError):
        validate_hourly_input(frame, emissions_reporting="regulatory_only")


def test_regulatory_only_rejects_wrong_factor_units() -> None:
    frame = _case()
    frame.attrs["emission_factor_sources"]["regulatory"]["unit"] = "t_CO2e/MWh"
    with pytest.raises(HourlyInputError):
        validate_hourly_input(frame, emissions_reporting="regulatory_only")


def test_regulatory_only_rejects_a_contradictory_factor_mode() -> None:
    frame = _case()
    frame.attrs["emission_factor_mode"] = "explicit_separate_factors"
    with pytest.raises(HourlyInputError):
        validate_hourly_input(frame, emissions_reporting="regulatory_only")


def test_regulatory_only_rejects_undeclared_extra_operational_sources() -> None:
    frame = _case()
    frame.attrs["emission_factor_sources"]["operational"] = _regulatory_source()
    with pytest.raises(HourlyInputError):
        validate_hourly_input(frame, emissions_reporting="regulatory_only")


@pytest.mark.parametrize("key", ["source_description", "reference_year", "spatial_scope", "unit", "emissions_basis"])
def test_regulatory_only_requires_each_source_field(key: str) -> None:
    frame = _case()
    del frame.attrs["emission_factor_sources"]["regulatory"][key]
    with pytest.raises(HourlyInputError):
        validate_hourly_input(frame, emissions_reporting="regulatory_only")


@pytest.mark.parametrize("year", [True, 2025.0, "2025", 1899, 2101])
def test_regulatory_only_rejects_invalid_source_reference_years(year: object) -> None:
    frame = _case()
    frame.attrs["emission_factor_sources"]["regulatory"]["reference_year"] = year
    with pytest.raises(HourlyInputError):
        validate_hourly_input(frame, emissions_reporting="regulatory_only")


@pytest.mark.parametrize("value", [np.nan, np.inf, -1.0])
def test_regulatory_only_rejects_invalid_regulatory_hourly_factors(value: float) -> None:
    frame = _case()
    frame.loc[7, "regulatory_grid_emission_factor"] = value
    with pytest.raises(HourlyInputError):
        validate_hourly_input(frame, emissions_reporting="regulatory_only")


@pytest.mark.parametrize("backend", ["gurobi", "scipy_highs"])
def test_regulatory_only_preserves_both_solver_paths_costs_dispatch_and_regulatory_result(backend: str) -> None:
    complete = optimize_hydrogen_system(_case(complete=True), solver_backend=backend)
    regulatory_only = optimize_hydrogen_system(
        _case(), solver_backend=backend, emissions_reporting="regulatory_only",
    )
    assert regulatory_only.objective_eur_per_year == pytest.approx(complete.objective_eur_per_year)
    assert regulatory_only.lcoh_eur_per_kg_h2 == pytest.approx(complete.lcoh_eur_per_kg_h2)
    assert regulatory_only.capacities == pytest.approx(complete.capacities)
    assert regulatory_only.annual_costs == pytest.approx(complete.annual_costs)
    assert regulatory_only.annual_h2_delivered_kg == pytest.approx(complete.annual_h2_delivered_kg)
    assert regulatory_only.annual_regulatory_emissions_kg_co2e == pytest.approx(complete.annual_regulatory_emissions_kg_co2e)
    assert complete.annual_grid_emissions_kg_co2e > 0.0
    assert regulatory_only.annual_regulatory_emissions_kg_co2e > 0.0
    assert regulatory_only.regulatory_emission_intensity_kg_co2e_per_kg_h2 == pytest.approx(complete.regulatory_emission_intensity_kg_co2e_per_kg_h2)
    assert regulatory_only.red_iii_ghg_compliant is complete.red_iii_ghg_compliant
    assert regulatory_only.annual_grid_emissions_kg_co2e is None
    assert regulatory_only.operational_emission_intensity_kg_co2e_per_kg_h2 is None
    assert regulatory_only.emissions_reporting == "regulatory_only"
    assert regulatory_only.operational_emissions_status == "not_evaluated"
    assert complete.emissions_reporting == "complete"
    assert complete.operational_emissions_status == "evaluated"
    assert not set(OPERATIONAL_HOURLY_COLUMNS).intersection(regulatory_only.hourly_operation.columns)
    for column in (
        "grid_import_mwh", "pv_generation_mwh", "wind_generation_mwh",
        "electrolyzer_electricity_mwh", "compressor_electricity_mwh",
        "h2_storage_level_kg", "regulatory_emissions_kg_co2e",
    ):
        np.testing.assert_allclose(regulatory_only.hourly_operation[column], complete.hourly_operation[column], atol=1e-8)


def test_single_runner_exports_null_operational_metrics_and_bound_contract(tmp_path: Path) -> None:
    input_path, contract_path = _write_contract(tmp_path / "source", _case())
    artifacts = run_single_site_h2(
        input_path, tmp_path / "results", solver_backend="scipy-highs",
        emission_factor_metadata_path=contract_path, emissions_reporting="regulatory_only",
    )
    _assert_absent_operational_exports(artifacts.output_directory)
    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert metadata["input"]["emission_factor_metadata"]["sha256"] == hashlib.sha256(contract_path.read_bytes()).hexdigest()
    assert metadata["input"]["sha256"] == hashlib.sha256(input_path.read_bytes()).hexdigest()
    assert artifacts.result.annual_grid_emissions_kg_co2e is None


def test_regulatory_only_sidecar_hash_must_match_exact_csv_bytes(tmp_path: Path) -> None:
    input_path, contract_path = _write_contract(tmp_path / "source", _case())
    input_path.write_bytes(input_path.read_bytes() + b"\n")
    with pytest.raises(H2RunError, match="Hash"):
        run_single_site_h2(
            input_path, tmp_path / "results", emission_factor_metadata_path=contract_path,
            emissions_reporting="regulatory_only",
        )
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("runner_name", ["single", "scenarios"])
def test_runners_reject_complete_default_before_solver_or_output_creation(tmp_path: Path, monkeypatch, runner_name: str) -> None:
    input_path, contract_path = _write_contract(tmp_path / "source", _case(pv=1.0))
    if runner_name == "single":
        import run_single_site_h2 as module
        runner = run_single_site_h2
        target = "optimize_hydrogen_system"
    else:
        import run_h2_scenarios as module
        runner = run_h2_scenarios
        target = "run_single_site_h2"
    def forbidden_solver(*args, **kwargs):
        pytest.fail("Default complete mode must reject unavailable operational factors before solving")
    monkeypatch.setattr(module, target, forbidden_solver)
    with pytest.raises(HourlyInputError):
        runner(input_path, tmp_path / "results", emission_factor_metadata_path=contract_path)
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("runner_name", ["single", "scenarios"])
def test_cli_explicitly_selects_regulatory_only_reporting(tmp_path: Path, runner_name: str) -> None:
    input_path, contract_path = _write_contract(tmp_path / "source", _case(pv=1.0))
    output = tmp_path / "results"
    main = single_main if runner_name == "single" else scenarios_main
    assert main([
        "--input", str(input_path), "--output-dir", str(output), "--solver", "scipy-highs",
        "--emission-factor-metadata", str(contract_path), "--emissions-reporting", "regulatory-only",
    ]) == 0
    directories = [output] if runner_name == "single" else [output / item for item in ("S0_reference", "S1_red_monthly", "S2_red_hourly")]
    for directory in directories:
        _assert_absent_operational_exports(directory)


def test_independent_validator_accepts_regulatory_only_exports(tmp_path: Path) -> None:
    root = _export_scenarios(tmp_path)
    artifacts = validate_h2_results(root, expected_hours=24)
    assert artifacts.all_checks_passed is True
    checks = pd.read_csv(artifacts.checks_path)
    assert checks["passed"].all()
    comparison = pd.read_csv(root / "scenario_comparison.csv")
    assert comparison.loc[:, list(OPERATIONAL_SUMMARY_COLUMNS)].isna().all().all()
    assert set(comparison["operational_emissions_status"]) == {"not_evaluated"}


@pytest.mark.parametrize("mutation", [
    "summary_zero", "metadata_zero", "hourly_placeholder", "extra_source",
    "missing_source", "evaluated_status", "source_content_changed",
    "original_csv_bytes_changed", "sidecar_csv_binding_changed",
    "sidecar_mode_changed", "sidecar_source_changed",
])
def test_independent_validator_rejects_false_operational_claims_and_missing_sources(tmp_path: Path, mutation: str) -> None:
    root = _export_scenarios(tmp_path)
    scenario = root / "S0_reference"
    if mutation == "summary_zero":
        path = scenario / "summary.csv"
        summary = pd.read_csv(path)
        summary.loc[0, list(OPERATIONAL_SUMMARY_COLUMNS)] = 0.0
        summary.to_csv(path, index=False)
    elif mutation == "hourly_placeholder":
        path = scenario / "hourly_operation.csv"
        operation = pd.read_csv(path)
        for column in OPERATIONAL_HOURLY_COLUMNS:
            operation[column] = 0.0
        operation.to_csv(path, index=False)
    else:
        path = scenario / "run_metadata.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if mutation == "metadata_zero":
            metadata["result"]["emissions"]["operational_grid_emissions_kg_co2e_per_year"] = 0.0
            metadata["result"]["emissions"]["operational_intensity_kg_co2e_per_kg_h2"] = 0.0
        elif mutation == "extra_source":
            metadata["input"]["emission_factor_sources"]["operational"] = deepcopy(_regulatory_source())
        elif mutation == "missing_source":
            del metadata["input"]["emission_factor_sources"]["regulatory"]
        elif mutation == "evaluated_status":
            metadata["result"]["operational_emissions_status"] = "evaluated"
        elif mutation == "source_content_changed":
            metadata["input"]["emission_factor_sources"]["regulatory"]["source_description"] = "Different synthetic source"
        elif mutation == "original_csv_bytes_changed":
            source_path = Path(metadata["input"]["source_path"])
            source_path.write_bytes(source_path.read_bytes() + b"\n")
        else:
            contract_path = Path(metadata["input"]["emission_factor_metadata"]["source_path"])
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            if mutation == "sidecar_csv_binding_changed":
                contract["input_sha256"] = "f" * 64
            elif mutation == "sidecar_mode_changed":
                contract["emission_factor_mode"] = "explicit_separate_factors"
            else:
                contract["emission_factor_sources"]["regulatory"]["source_description"] = "Different synthetic source"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            # Preserve the metadata SHA to isolate contract semantics from a
            # simple checksum failure for this one scenario.
            metadata["input"]["emission_factor_metadata"]["sha256"] = hashlib.sha256(contract_path.read_bytes()).hexdigest()
        path.write_text(json.dumps(metadata), encoding="utf-8")
    artifacts = validate_h2_results(root, expected_hours=24)
    assert artifacts.all_checks_passed is False
    checks = pd.read_csv(artifacts.checks_path)
    assert (~checks["passed"]).any()
    reference_checks = checks.loc[checks["scenario"] == "reference"]
    assert (~reference_checks["passed"]).any()
